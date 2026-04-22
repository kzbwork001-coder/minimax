"""Tests for recv-loop robustness: malformed payloads, per-seq future failure, and
cleanup when the loop exits. Regression coverage for the bug where a pydantic
validation error on a SyncRes zombied the client (ping task kept firing but
pending requests hung forever).
"""

import asyncio
import json

import pytest

from minimax.client.webclient import WebClient
from minimax.schema import Opcode


class FakeWs:
    """Minimal async-iterable stand-in for `websockets.ClientConnection`.

    Yields each pre-loaded message once, then signals EOF by raising
    `StopAsyncIteration`.
    """

    def __init__(self, messages):
        self._messages = list(messages)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


def _make_client() -> WebClient:
    return WebClient(phone=71234567890, token=None)


class TestRecvLoopPerMessageValidation:
    async def test_malformed_schema_fails_only_that_pending_future(self):
        """A response payload that fails pydantic validation should fail the pending
        future for that specific seq rather than silently dropping it (which used to
        hang the caller forever)."""
        client = _make_client()
        loop = asyncio.get_running_loop()
        fut_sync = loop.create_future()
        fut_ping = loop.create_future()
        client._pending[5] = fut_sync
        client._pending[7] = fut_ping

        # SyncRes is missing the required `profile` field — pydantic will raise.
        bad_sync = json.dumps(
            {"ver": 11, "cmd": 0, "seq": 5, "opcode": Opcode.SYNC.value,
             "payload": {"chats": [], "contacts": []}}
        )
        # Valid PING reply (payload=null -> EmptyPayload).
        good_ping = json.dumps(
            {"ver": 11, "cmd": 0, "seq": 7, "opcode": Opcode.PING.value, "payload": None}
        )
        client._ws = FakeWs([bad_sync, good_ping])

        await client._recv_loop()

        # The bad SYNC future was failed (not left hanging).
        assert fut_sync.done()
        with pytest.raises(Exception):
            fut_sync.result()
        # The good PING future was resolved normally — the loop kept running.
        assert fut_ping.done()
        assert fut_ping.exception() is None
        assert fut_ping.result().opcode == Opcode.PING

    async def test_malformed_json_does_not_kill_loop(self):
        """Unparseable JSON should be logged and skipped, not raised out of the loop."""
        client = _make_client()
        loop = asyncio.get_running_loop()
        fut_ping = loop.create_future()
        client._pending[3] = fut_ping

        garbage = "this is not json {"
        good_ping = json.dumps(
            {"ver": 11, "cmd": 0, "seq": 3, "opcode": Opcode.PING.value, "payload": None}
        )
        client._ws = FakeWs([garbage, good_ping])

        await client._recv_loop()

        # Loop survived the garbage message and resolved the later valid one.
        assert fut_ping.done()
        assert fut_ping.exception() is None

    async def test_unknown_opcode_is_skipped(self):
        """`build_wrapper` returns None for opcodes not in the schema; loop should skip."""
        client = _make_client()
        loop = asyncio.get_running_loop()
        fut_ping = loop.create_future()
        client._pending[4] = fut_ping

        unknown = json.dumps({"ver": 11, "cmd": 0, "seq": 99, "opcode": 9999, "payload": None})
        good_ping = json.dumps(
            {"ver": 11, "cmd": 0, "seq": 4, "opcode": Opcode.PING.value, "payload": None}
        )
        client._ws = FakeWs([unknown, good_ping])

        await client._recv_loop()

        assert fut_ping.done()
        assert fut_ping.exception() is None


class TestRecvLoopExitCleanup:
    async def test_exit_cancels_ping_task_and_fails_pending(self):
        """When the recv loop exits for any reason, every still-pending request future
        must be failed and the ping task must be cancelled — otherwise the client is
        a zombie (half-dead connection still pinging, callers hanging forever)."""
        client = _make_client()

        async def forever():
            await asyncio.sleep(1000)

        ping_task = asyncio.create_task(forever())
        client._ping_task = ping_task

        loop = asyncio.get_running_loop()
        fut_a = loop.create_future()
        fut_b = loop.create_future()
        client._pending[1] = fut_a
        client._pending[2] = fut_b

        # Empty FakeWs → recv loop sees StopAsyncIteration immediately → finally fires.
        client._ws = FakeWs([])

        await client._recv_loop()
        await asyncio.sleep(0)  # let the cancelled ping task settle

        assert ping_task.cancelled() or ping_task.done()
        for fut in (fut_a, fut_b):
            assert fut.done()
            with pytest.raises(ConnectionError):
                fut.result()
        assert client._pending == {}

    async def test_exit_does_not_overwrite_already_resolved_futures(self):
        """If a future was already resolved before the loop exited, the cleanup
        pass must not try to set another exception on it."""
        client = _make_client()
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        client._pending[3] = fut

        good_ping = json.dumps(
            {"ver": 11, "cmd": 0, "seq": 3, "opcode": Opcode.PING.value, "payload": None}
        )
        client._ws = FakeWs([good_ping])

        await client._recv_loop()

        assert fut.done()
        assert fut.exception() is None  # not overwritten by cleanup

    async def test_exit_with_no_ping_task_is_safe(self):
        """Cleanup must not crash when `_ping_task` is None (loop exits before `_start`
        has spawned it)."""
        client = _make_client()
        assert client._ping_task is None

        client._ws = FakeWs([])
        await client._recv_loop()
        # No exception is success.
