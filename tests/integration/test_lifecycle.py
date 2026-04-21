"""Integration tests for the client lifecycle (_start, INIT flow)."""

import asyncio
import uuid

import pytest

from minimax.schema import Opcode
from minimax.schema.responses import UserAgentRes


class TestClientStart:
    async def test_start_sends_init(self, mock_transport):
        mock_transport.set_response(
            Opcode.INIT,
            UserAgentRes(location="RU"),
        )

        # _start spawns a recv loop; our mock's recv loop just waits forever
        try:
            await asyncio.wait_for(mock_transport._start(), timeout=1.0)
        finally:
            await mock_transport._stop()

        init_calls = [s for s in mock_transport.sent if s[0] == Opcode.INIT]
        assert len(init_calls) == 1
        payload = init_calls[0][1]
        assert isinstance(payload.device_id, uuid.UUID)

    async def test_stop_cancels_background_tasks(self, mock_transport):
        mock_transport.set_response(Opcode.INIT, UserAgentRes(location="RU"))

        await mock_transport._start()
        recv_task = mock_transport._recv_task
        ping_task = mock_transport._ping_task
        assert recv_task is not None
        assert ping_task is not None

        await mock_transport._stop()

        # Tasks should be cancelled after _stop
        # (give event loop a tick to let cancellation propagate)
        await asyncio.sleep(0)
        assert recv_task.cancelled() or recv_task.done()
        assert ping_task.cancelled() or ping_task.done()
