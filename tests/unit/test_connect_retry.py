"""Tests for connection retry logic in TcpTransport and WsTransport."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from minimax.client.tcp import TcpTransport
from minimax.client.ws import WsTransport
from minimax.constants import CONNECT_MAX_ATTEMPTS


class TestTcpConnectRetry:
    @pytest.mark.asyncio
    async def test_raises_timeout_after_max_attempts(self):
        transport = TcpTransport(phone=71234567890)
        with patch("minimax.client.tcp.asyncio.open_connection", new_callable=AsyncMock, side_effect=TimeoutError("timed out")):
            with pytest.raises(TimeoutError, match=f"after {CONNECT_MAX_ATTEMPTS} attempts"):
                await transport._connect()

    @pytest.mark.asyncio
    async def test_succeeds_on_second_attempt(self):
        transport = TcpTransport(phone=71234567890)
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_writer.get_extra_info.return_value = None

        call_count = 0

        async def open_connection_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("timed out")
            return mock_reader, mock_writer

        with patch("minimax.client.tcp.asyncio.open_connection", side_effect=open_connection_side_effect):
            await transport._connect()

        assert transport._reader is mock_reader
        assert transport._writer is mock_writer
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_non_timeout_exception_propagates_immediately(self):
        transport = TcpTransport(phone=71234567890)
        with patch("minimax.client.tcp.asyncio.open_connection", new_callable=AsyncMock, side_effect=ConnectionRefusedError("refused")):
            with pytest.raises(ConnectionRefusedError):
                await transport._connect()


class TestWsConnectRetry:
    @pytest.mark.asyncio
    async def test_raises_timeout_after_max_attempts(self):
        transport = WsTransport(phone=71234567890)
        with patch("minimax.client.ws.websockets.connect", new_callable=AsyncMock, side_effect=TimeoutError("timed out")):
            with pytest.raises(TimeoutError, match=f"after {CONNECT_MAX_ATTEMPTS} attempts"):
                await transport._connect()

    @pytest.mark.asyncio
    async def test_succeeds_on_second_attempt(self):
        transport = WsTransport(phone=71234567890)
        mock_ws = AsyncMock()

        call_count = 0

        async def connect_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("timed out")
            return mock_ws

        with patch("minimax.client.ws.websockets.connect", side_effect=connect_side_effect):
            await transport._connect()

        assert transport._ws == mock_ws
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_non_timeout_exception_propagates_immediately(self):
        transport = WsTransport(phone=71234567890)
        with patch("minimax.client.ws.websockets.connect", new_callable=AsyncMock, side_effect=OSError("network unreachable")):
            with pytest.raises(OSError):
                await transport._connect()
