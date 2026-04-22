"""Integration regression test for the SyncRes-validation-zombie bug.

Scenario the user hit in production:
  1. Client sends SYNC.
  2. Server sends a SyncRes whose `chats[0].lastMessage.sender` is missing.
  3. Pydantic raises ValidationError inside `build_wrapper`; the WS recv loop
     dies; but the ping task keeps running and the pending SYNC future is
     never resolved nor failed, so `sync()` hangs forever and the upstream
     FastAPI WebSocket handler stays open indefinitely.

After the fix:
  - Even if the schema is buggy, the recv loop fails the specific pending
    future with the ValidationError and keeps running (per-item recovery).
  - When the recv loop does exit, the ping task is cancelled and all other
    pending futures are failed so callers unhook cleanly.
"""

import asyncio
import json

import pytest

from minimax.client.webclient import WebClient
from minimax.constants import PING_INTERVAL_SECONDS
from minimax.schema import Opcode


class ScriptedWs:
    """An async-iterable ws stand-in that yields messages on command so the test
    can interleave recv/send steps instead of pre-loading everything."""

    def __init__(self):
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()
        self.sent: list[str] = []

    def push(self, message: str) -> None:
        self._queue.put_nowait(message)

    def close(self) -> None:
        self._queue.put_nowait(None)

    def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self._queue.get()
        if msg is None:
            raise StopAsyncIteration
        return msg

    async def send(self, raw: str) -> None:
        self.sent.append(raw)


class TestSyncResZombieRegression:
    async def test_malformed_sync_response_does_not_zombie_client(self):
        """`sync()` must raise promptly on a malformed SyncRes instead of hanging
        forever while the ping task keeps firing."""
        client = WebClient(phone=71234567890, token=None)
        ws = ScriptedWs()
        client._ws = ws

        # Stand in a ping task so we can assert it gets cancelled on recv-loop exit.
        async def forever():
            await asyncio.sleep(PING_INTERVAL_SECONDS * 1000)

        client._ping_task = asyncio.create_task(forever())

        recv_task = asyncio.create_task(client._recv_loop())

        # Act: the caller issues a SYNC. `_send` stores the pending future at
        # self._seq, which starts at 0 and increments to 1 for this first send.
        sync_future = asyncio.create_task(client.sync("tok"))
        await asyncio.sleep(0)  # let _send run and register the pending future

        assert 1 in client._pending, "sync() should have registered a pending future"

        # Server replies with a SyncRes missing the required `profile` field —
        # exactly the shape of failure the production bug produced.
        ws.push(json.dumps({
            "ver": 11, "cmd": 0, "seq": 1, "opcode": Opcode.SYNC.value,
            "payload": {"chats": [], "contacts": []},
        }))

        # `sync()` must surface the validation failure promptly, not hang.
        with pytest.raises(Exception) as exc_info:
            await asyncio.wait_for(sync_future, timeout=1.0)
        assert "profile" in str(exc_info.value).lower()

        # The recv loop itself keeps running after a per-item failure (other
        # requests on the same connection can still succeed).
        assert not recv_task.done()

        # Close the ws — recv loop should exit cleanly and cancel the ping task.
        ws.close()
        await asyncio.wait_for(recv_task, timeout=1.0)
        await asyncio.sleep(0)
        assert client._ping_task.cancelled() or client._ping_task.done()

    async def test_recv_loop_termination_unhooks_all_pending_callers(self):
        """If the recv loop exits (e.g., server closes the ws), every in-flight
        request must fail — not hang forever."""
        client = WebClient(phone=71234567890, token=None)
        ws = ScriptedWs()
        client._ws = ws

        async def forever():
            await asyncio.sleep(PING_INTERVAL_SECONDS * 1000)

        client._ping_task = asyncio.create_task(forever())

        recv_task = asyncio.create_task(client._recv_loop())

        sync_future = asyncio.create_task(client.sync("tok"))
        await asyncio.sleep(0)
        assert 1 in client._pending

        # Server closes without replying.
        ws.close()

        with pytest.raises(ConnectionError):
            await asyncio.wait_for(sync_future, timeout=1.0)

        await asyncio.wait_for(recv_task, timeout=1.0)
        await asyncio.sleep(0)
        assert client._ping_task.cancelled() or client._ping_task.done()
        assert client._pending == {}
