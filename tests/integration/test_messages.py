"""Integration tests for fetching messages with pagination."""

from datetime import datetime

from minimax.schema import Opcode
from minimax.schema.models import Message
from minimax.schema.responses import MessagesRes


def _make_msg(mid: int, ts_ms: int, text: str = "hi") -> Message:
    return Message(id=mid, sender=1, text=text, time=ts_ms, type="TEXT")


class TestFetchMessages:
    async def test_single_page(self, mock_transport):
        ts_from = int(datetime(2026, 1, 1).timestamp()) * 1000
        ts_to = int(datetime(2026, 1, 2).timestamp()) * 1000
        mid_ts = (ts_from + ts_to) // 2

        mock_transport.set_response(
            Opcode.MESSAGES,
            MessagesRes(messages=[_make_msg(1, mid_ts)]),
        )

        result = await mock_transport.fetch_messages(
            chat_id=100,
            history_from=datetime(2026, 1, 1),
            history_to=datetime(2026, 1, 2),
        )

        assert len(result) == 1
        assert result[0].id == 1

    async def test_empty_response_stops_pagination(self, mock_transport):
        mock_transport.set_response(Opcode.MESSAGES, MessagesRes(messages=[]))

        result = await mock_transport.fetch_messages(
            chat_id=100,
            history_from=datetime(2026, 1, 1),
            history_to=datetime(2026, 1, 2),
        )

        assert result == []
        # Only one request should have been sent
        message_calls = [s for s in mock_transport.sent if s[0] == Opcode.MESSAGES]
        assert len(message_calls) == 1

    async def test_filters_messages_outside_range(self, mock_transport):
        ts_from = int(datetime(2026, 1, 1).timestamp()) * 1000
        ts_to = int(datetime(2026, 1, 2).timestamp()) * 1000
        ts_before = ts_from - 10000
        ts_in = ts_from + 1000

        mock_transport.set_response(
            Opcode.MESSAGES,
            MessagesRes(messages=[_make_msg(2, ts_in), _make_msg(1, ts_before)]),
        )

        result = await mock_transport.fetch_messages(
            chat_id=100,
            history_from=datetime(2026, 1, 1),
            history_to=datetime(2026, 1, 2),
        )

        # Only the in-range message should be returned
        assert len(result) == 1
        assert result[0].id == 2

    async def test_sends_correct_chat_id(self, mock_transport):
        mock_transport.set_response(Opcode.MESSAGES, MessagesRes(messages=[]))

        await mock_transport.fetch_messages(
            chat_id=555,
            history_from=datetime(2026, 1, 1),
            history_to=datetime(2026, 1, 2),
        )

        opcode, payload = mock_transport.sent[0]
        assert opcode == Opcode.MESSAGES
        assert payload.chat_id == 555
        assert payload.backward == 100
