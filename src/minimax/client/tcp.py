import asyncio
import logging
import socket
import ssl
from typing import Any
from uuid import UUID

import lz4.block
import msgpack

from ..constants import (
    CONNECT_MAX_ATTEMPTS,
    CONNECT_RETRY_DELAY,
    RECV_LOOP_BACKOFF_DELAY,
    SOCKET_HOST,
    SOCKET_PORT,
)
from ..schema import (
    OPCODE_SCHEMA,
    EmptyPayload,
    Opcode,
    Wrapper,
)
from .client import Client

log = logging.getLogger(__name__)

# lz4.block.decompress requires an upper bound on the uncompressed size when the
# source was not compressed with store_size=True. The MAX server doesn't store
# the size, so we retry with progressively larger ceilings. Caps are powers of
# two; 64MB is well above anything the server has been observed to send for a
# single packet.
_LZ4_DECOMPRESS_MAX_SIZES = (1 << 20, 1 << 23, 1 << 26)


class DecompressError(Exception):
    """Raised by unpack_items when an lz4 packet cannot be decompressed.

    Carries the seq so the recv loop can fail the matching pending future
    instead of silently dropping the response (which would leave the awaiting
    caller hung forever).
    """

    def __init__(self, seq: int, opcode: int, payload_length: int):
        super().__init__(
            f"LZ4 decompression failed for seq={seq} opcode={opcode} "
            f"payload_len={payload_length} (exceeded {_LZ4_DECOMPRESS_MAX_SIZES[-1]} bytes)"
        )
        self.seq = seq
        self.opcode = opcode

# Header layout (10 bytes total):
#   [0:1]  ver     (1 byte)
#   [1:3]  cmd     (2 bytes)
#   [3:4]  seq     (1 byte, 0-255)
#   [4:6]  opcode  (2 bytes)
#   [6:10] packed_len (4 bytes: top byte = lz4 compression flag, lower 3 bytes = payload length)
HEADER_SIZE = 10


def _msgpack_default(obj: Any) -> Any:
    """Handle types that msgpack cannot serialize natively."""
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Cannot serialize {type(obj).__name__} object")


def pack(wrapper: Wrapper) -> bytes:
    """Serialize a Wrapper into a binary packet (header + msgpack payload)."""
    ver_b = wrapper.ver.to_bytes(1, "big")
    cmd_b = wrapper.cmd.to_bytes(2, "big")
    # seq field is 1 byte, so we wrap the monotonic counter to fit 0-255
    seq_b = (wrapper.seq % 256).to_bytes(1, "big")
    opcode_b = wrapper.opcode.value.to_bytes(2, "big")
    payload = wrapper.payload
    payload_dict = payload.model_dump(by_alias=True) if not isinstance(payload, EmptyPayload) else {}
    payload_bytes = msgpack.packb(payload_dict, default=_msgpack_default) or b""
    payload_len_b = len(payload_bytes).to_bytes(4, "big")
    log.debug("pack: seq=%d opcode=%s payload=%s", wrapper.seq % 256, wrapper.opcode.name, payload_dict)
    return ver_b + cmd_b + seq_b + opcode_b + payload_len_b + payload_bytes


def unpack_items(data: bytes) -> list[dict]:
    """Deserialize a binary packet into a list of raw header+payload dicts.

    Pydantic validation is intentionally NOT performed here so the caller can
    decide what to do per-item when validation fails (for example, fail the
    corresponding pending request future for that ``seq`` rather than silently
    dropping the response).

    Returns a list because the server may batch multiple items in a single
    packet by sending a list as the msgpack payload.
    """
    if len(data) < HEADER_SIZE:
        return []
    ver = int.from_bytes(data[0:1], "big")
    cmd = int.from_bytes(data[1:3], "big")
    seq = int.from_bytes(data[3:4], "big")
    opcode = int.from_bytes(data[4:6], "big")
    packed_len = int.from_bytes(data[6:10], "big")
    # packed_len encodes two things: the top byte is the lz4 compression flag,
    # the lower 3 bytes are the actual payload length
    compression_flag = packed_len >> 24
    payload_length = packed_len & 0x00FFFFFF
    payload_bytes = data[HEADER_SIZE : HEADER_SIZE + payload_length]

    raw_payload = None
    if payload_bytes:
        if compression_flag != 0:
            decompressed: bytes | None = None
            for max_size in _LZ4_DECOMPRESS_MAX_SIZES:
                try:
                    decompressed = lz4.block.decompress(payload_bytes, uncompressed_size=max_size)
                    break
                except lz4.block.LZ4BlockError:
                    continue
            if decompressed is None:
                raise DecompressError(seq=seq, opcode=opcode, payload_length=payload_length)
            payload_bytes = decompressed
        raw_payload = msgpack.unpackb(payload_bytes, raw=False, strict_map_key=False)

    log.debug(
        "unpack: seq=%d opcode=%d lz4=%s payload_len=%d raw=%s",
        seq,
        opcode,
        compression_flag != 0,
        payload_length,
        raw_payload,
    )

    header = {"ver": ver, "cmd": cmd, "seq": seq, "opcode": opcode}
    return (
        [{**header, "payload": obj} for obj in raw_payload]
        if isinstance(raw_payload, list)
        else [{**header, "payload": raw_payload}]
    )


def _create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.set_ciphers("DEFAULT")
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


class TcpTransport(Client):
    """TCP socket transport using asyncio streams. Handles TLS, send/recv over a binary protocol."""

    def __init__(self, phone: int | None, token: str | None = None):
        super().__init__(phone, token)
        self._host = SOCKET_HOST
        self._port = SOCKET_PORT
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def _connect(self) -> None:
        ssl_ctx = _create_ssl_context()
        for attempt in range(1, CONNECT_MAX_ATTEMPTS + 1):
            try:
                log.info("Connecting to %s:%s via TCP socket (attempt %d/%d)", self._host, self._port, attempt, CONNECT_MAX_ATTEMPTS)
                self._reader, self._writer = await asyncio.open_connection(
                    self._host, self._port, ssl=ssl_ctx, server_hostname=self._host
                )
                sock = self._writer.get_extra_info("socket")
                if sock is not None:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                return
            except (TimeoutError, asyncio.TimeoutError, socket.gaierror, ConnectionResetError) as e:
                log.warning("TCP connection attempt %d/%d failed (%s): %s", attempt, CONNECT_MAX_ATTEMPTS, type(e).__name__, e)
                if attempt < CONNECT_MAX_ATTEMPTS:
                    await asyncio.sleep(CONNECT_RETRY_DELAY)
        raise TimeoutError(f"Failed to connect to {self._host}:{self._port} after {CONNECT_MAX_ATTEMPTS} attempts")

    async def _disconnect(self) -> None:
        writer = self._writer
        self._reader = None
        self._writer = None
        if writer is not None:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                log.debug("Error closing writer", exc_info=True)

    async def _recv_loop(self) -> None:
        if self._reader is None:
            log.warning("Recv loop started without reader")
            return

        reader = self._reader
        try:
            while self._reader is not None:
                try:
                    header = await reader.readexactly(HEADER_SIZE)
                    packed_len = int.from_bytes(header[6:10], "big")
                    payload_length = packed_len & 0x00FFFFFF
                    payload = await reader.readexactly(payload_length) if payload_length else b""
                    raw_packet = header + payload

                    try:
                        items = unpack_items(raw_packet)
                    except DecompressError as e:
                        log.error("%s", e)
                        future = self._pending.pop(e.seq, None)
                        if future and not future.done():
                            future.set_exception(e)
                        else:
                            log.warning("seq=%d decompress failed but no pending future", e.seq)
                        continue

                    for item in items:
                        seq_key = item.get("seq")
                        try:
                            wrapper = Client.build_wrapper(item)
                        except Exception as e:
                            log.exception("Failed to build wrapper (seq=%s): %s", seq_key, e)
                            future = self._pending.pop(seq_key, None) if seq_key is not None else None
                            if future and not future.done():
                                future.set_exception(e)
                            continue
                        if wrapper is None:
                            continue
                        log.debug("recv: seq=%d opcode=%s payload=%s", wrapper.seq, wrapper.opcode.name, wrapper.payload)
                        future = self._pending.pop(wrapper.seq, None)
                        if future and not future.done():
                            future.set_result(wrapper)
                        else:
                            log.debug("seq=%d has no pending future (opcode=%s)", wrapper.seq, wrapper.opcode.name)

                except asyncio.IncompleteReadError as e:
                    log.info("Socket connection closed; exiting recv loop (read %d/%d bytes)", len(e.partial), e.expected)
                    break
                except asyncio.CancelledError:
                    log.debug("Recv loop cancelled")
                    raise
                except ConnectionError as e:
                    log.error("Connection error in recv_loop: %s", e)
                    break
                except OSError as e:
                    log.error("Socket OS error in recv_loop: %s", e)
                    break
                except Exception as e:
                    log.exception("Unexpected error in recv_loop: %s; backing off briefly", e)
                    await asyncio.sleep(RECV_LOOP_BACKOFF_DELAY)
        finally:
            self._fail_pending_and_stop_ping(ConnectionError("minimax recv loop terminated"))

    async def _send(self, opcode: Opcode, **kwargs: Any) -> asyncio.Future[Wrapper]:
        if self._writer is None:
            raise ConnectionError("Socket not connected")

        req_type, _ = OPCODE_SCHEMA[opcode]
        payload_model = req_type(**kwargs)  # type: ignore[call-arg]
        self._seq += 1
        seq = self._seq
        seq_key = seq % 256

        wrapper = Wrapper(opcode=opcode, seq=seq, payload=payload_model)

        old_future = self._pending.pop(seq_key, None)
        if old_future and not old_future.done():
            log.warning("seq=%d already pending, cancelling old future", seq_key)
            old_future.cancel()

        future: asyncio.Future[Wrapper] = asyncio.get_running_loop().create_future()
        self._pending[seq_key] = future

        packet = pack(wrapper)
        log.debug("send seq=%d %s (%d bytes)", seq_key, opcode.name, len(packet))
        self._writer.write(packet)
        await self._writer.drain()
        return future
