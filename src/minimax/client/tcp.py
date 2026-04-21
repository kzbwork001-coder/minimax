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


def unpack(data: bytes) -> list[Wrapper]:
    """Deserialize a binary packet into a list of Wrappers.

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
            try:
                payload_bytes = lz4.block.decompress(payload_bytes, uncompressed_size=99999)
            except lz4.block.LZ4BlockError:
                log.warning("LZ4 decompression failed, skipping packet")
                return []
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
    items = (
        [{**header, "payload": obj} for obj in raw_payload]
        if isinstance(raw_payload, list)
        else [{**header, "payload": raw_payload}]
    )

    wrappers = []
    for item in items:
        w = Client.build_wrapper(item)
        if w is not None:
            wrappers.append(w)
    return wrappers


def _create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.set_ciphers("DEFAULT")
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


class TcpTransport(Client):
    """TCP socket transport layer. Handles connection, send/recv over a binary protocol."""

    def __init__(self, phone: int | None, token: str | None = None):
        super().__init__(phone, token)
        self._host = SOCKET_HOST
        self._port = SOCKET_PORT
        self._socket: socket.socket | None = None

    async def _connect(self) -> None:
        for attempt in range(1, CONNECT_MAX_ATTEMPTS + 1):
            try:
                log.info("Connecting to %s:%s via TCP socket (attempt %d/%d)", self._host, self._port, attempt, CONNECT_MAX_ATTEMPTS)
                loop = asyncio.get_running_loop()
                ssl_ctx = _create_ssl_context()
                raw_sock = await loop.run_in_executor(None, lambda: socket.create_connection((self._host, self._port)))
                self._socket = ssl_ctx.wrap_socket(raw_sock, server_hostname=self._host)
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # type: ignore[call-arg]
                return
            except TimeoutError as e:
                log.warning("TCP connection attempt %d/%d timed out: %s", attempt, CONNECT_MAX_ATTEMPTS, e)
                if attempt < CONNECT_MAX_ATTEMPTS:
                    await asyncio.sleep(CONNECT_RETRY_DELAY)
        raise TimeoutError(f"Failed to connect to {self._host}:{self._port} after {CONNECT_MAX_ATTEMPTS} attempts")

    async def _disconnect(self) -> None:
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                log.debug("Error closing socket", exc_info=True)
            self._socket = None

    @staticmethod
    def _get_socket_bytes(sock: socket.socket, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                return bytes(buf)
            buf.extend(chunk)
        return bytes(buf)

    async def _recv_loop(self) -> None:
        if self._socket is None:
            log.warning("Recv loop started without socket")
            return

        sock = self._socket
        loop = asyncio.get_running_loop()

        while self._socket is not None:
            try:
                header = await loop.run_in_executor(None, lambda: self._get_socket_bytes(sock, HEADER_SIZE))
                if not header or len(header) < HEADER_SIZE:
                    log.info("Socket connection closed; exiting recv loop")
                    break

                packed_len = int.from_bytes(header[6:10], "big")
                payload_length = packed_len & 0x00FFFFFF
                payload = bytearray()
                remaining = payload_length

                # TCP is a stream protocol — a single recv() may return fewer bytes
                # than requested. This inner loop collects chunks until the full
                # payload (whose size we know from the header) has been received.
                while remaining > 0:
                    chunk_size = min(remaining, 8192)
                    chunk = await loop.run_in_executor(None, lambda cs=chunk_size: self._get_socket_bytes(sock, cs))
                    if not chunk:
                        log.error("Connection closed while reading payload")
                        break
                    payload.extend(chunk)
                    remaining -= len(chunk)

                if remaining > 0:
                    log.error("Incomplete payload received; skipping packet")
                    continue

                raw_packet = header + payload
                wrappers = unpack(raw_packet)

                for wrapper in wrappers:
                    seq_key = wrapper.seq
                    log.debug("recv: seq=%d opcode=%s payload=%s", seq_key, wrapper.opcode.name, wrapper.payload)
                    future = self._pending.pop(seq_key, None)
                    if future and not future.done():
                        future.set_result(wrapper)
                    else:
                        log.debug("seq=%d has no pending future (opcode=%s)", seq_key, wrapper.opcode.name)

            except asyncio.CancelledError as e:
                log.debug("Recv loop cancelled: %s", e)
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

    async def _send(self, opcode: Opcode, **kwargs: Any) -> asyncio.Future[Wrapper]:
        if self._socket is None:
            raise ConnectionError("Socket not connected")

        self._seq += 1
        seq = self._seq
        # seq field in the binary header is 1 byte (0-255), so we use seq % 256
        # as the pending-future key to match requests with responses
        seq_key = seq % 256

        req_type, _ = OPCODE_SCHEMA[opcode]
        payload_model = req_type(**kwargs)  # type: ignore[call-arg]
        wrapper = Wrapper(opcode=opcode, seq=seq, payload=payload_model)

        old_future = self._pending.pop(seq_key, None)
        if old_future and not old_future.done():
            log.warning("seq=%d already pending, cancelling old future", seq_key)
            old_future.cancel()

        future: asyncio.Future[Wrapper] = asyncio.get_running_loop().create_future()
        self._pending[seq_key] = future

        packet = pack(wrapper)
        log.debug("send seq=%d %s (%d bytes)", seq_key, opcode.name, len(packet))

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self._socket.sendall(packet))  # type: ignore[call-arg]
        return future
