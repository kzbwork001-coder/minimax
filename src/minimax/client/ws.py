import asyncio
import json
import logging
from asyncio import Future, get_event_loop
from typing import Any, override

import websockets
from websockets.asyncio.client import ClientConnection

from ..constants import CONNECT_MAX_ATTEMPTS, CONNECT_RETRY_DELAY, USER_AGENT, WEBSOCKET_ORIGIN, WEBSOCKET_URI
from ..schema import OPCODE_SCHEMA, Opcode, Wrapper
from .client import Client

log = logging.getLogger(__name__)


class WsTransport(Client):
    """WebSocket transport layer. Handles connection, send/recv over JSON-WS."""

    def __init__(self, phone: str | None, token: str | None = None):
        super().__init__(phone, token)
        self._ws: ClientConnection | None = None

    @override
    async def _connect(self) -> None:
        for attempt in range(1, CONNECT_MAX_ATTEMPTS + 1):
            try:
                log.info("Connecting to %s (attempt %d/%d)", WEBSOCKET_URI, attempt, CONNECT_MAX_ATTEMPTS)
                self._ws = await websockets.connect(
                    uri=WEBSOCKET_URI, origin=WEBSOCKET_ORIGIN, user_agent_header=USER_AGENT, ping_interval=None
                )
                return
            except TimeoutError as e:
                log.warning("WebSocket connection attempt %d/%d timed out: %s", attempt, CONNECT_MAX_ATTEMPTS, e)
                if attempt < CONNECT_MAX_ATTEMPTS:
                    await asyncio.sleep(CONNECT_RETRY_DELAY)
        raise TimeoutError(f"Failed to connect to {WEBSOCKET_URI} after {CONNECT_MAX_ATTEMPTS} attempts")

    @override
    async def _disconnect(self) -> None:
        if self._ws:
            await self._ws.close()

    @override
    async def _recv_loop(self) -> None:
        """Receive messages from the server and dispatch them to the appropriate future."""
        if not self._ws:
            log.error("Can't start receiving loop, client is disconnected")
            return

        async for raw_msg in self._ws:
            log.debug("recv: %s", raw_msg)
            wrapper = Client.build_wrapper(json.loads(raw_msg))
            if wrapper is None:
                continue
            future = self._pending.pop(wrapper.seq, None)
            if future and not future.done():
                log.debug("seq=%d resolved -> %s", wrapper.seq, wrapper.opcode.name)
                future.set_result(wrapper)
            else:
                log.warning("seq=%d has no pending future, dropping", wrapper.seq)

    @override
    async def _send(self, opcode: Opcode, **kwargs: Any) -> Future[Wrapper]:
        """Send a request to the server and return a future for the response."""
        self._seq += 1
        seq = self._seq
        req_type, _ = OPCODE_SCHEMA[opcode]
        payload = req_type(**kwargs)  # type: ignore[call-arg]
        wrapper = Wrapper(opcode=opcode, seq=seq, payload=payload)
        old_future = self._pending.pop(seq, None)
        if old_future and not old_future.done():
            log.warning("seq=%d already pending, cancelling old future", seq)
            old_future.cancel()
        future: Future[Wrapper] = get_event_loop().create_future()
        self._pending[seq] = future
        raw = wrapper.to_json()
        log.debug("send seq=%d %s: %s", seq, opcode.name, raw)
        await self._ws.send(raw)
        return future
