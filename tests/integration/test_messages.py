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

        # Server returns each page oldest-first.
        mock_transport.set_response(
            Opcode.MESSAGES,
            MessagesRes(messages=[_make_msg(1, ts_before), _make_msg(2, ts_in)]),
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

    async def test_limit_caps_result_size_within_single_page(self, mock_transport):
        """When a single page already contains more than `limit` in-range messages,
        the result must be truncated to exactly `limit` without fetching more pages."""
        ts_from = int(datetime(2026, 1, 1).timestamp()) * 1000
        ts_to = int(datetime(2026, 1, 2).timestamp()) * 1000
        step = (ts_to - ts_from) // 10
        # Oldest-first: id=9 has the oldest time, id=1 the newest.
        page = [_make_msg(i, ts_to - i * step) for i in range(9, 0, -1)]
        mock_transport.set_response(Opcode.MESSAGES, MessagesRes(messages=page))

        result = await mock_transport.fetch_messages(
            chat_id=100,
            history_from=datetime(2026, 1, 1),
            history_to=datetime(2026, 1, 2),
            limit=3,
        )

        assert len(result) == 3
        assert [m.id for m in result] == [1, 2, 3]
        # Only the first page was requested — pagination stopped early.
        assert len([s for s in mock_transport.sent if s[0] == Opcode.MESSAGES]) == 1

    async def test_limit_stops_pagination_across_pages(self, mock_transport):
        """When `limit` is reached mid-second-page, no further backward pages are
        fetched. This is the whole point of the parameter — bounding the API cost
        when the caller only wants the N most recent messages."""
        ts_from = int(datetime(2026, 1, 1).timestamp()) * 1000
        ts_to = int(datetime(2026, 1, 2).timestamp()) * 1000
        step = (ts_to - ts_from) // 250

        # Two full pages of 100, each oldest-first as the server returns them.
        # With limit=50 we expect exactly one MESSAGES request.
        pages = [
            [_make_msg(i, ts_to - i * step) for i in range(100, 0, -1)],
            [_make_msg(i, ts_to - i * step) for i in range(200, 100, -1)],
        ]
        call_count = {"n": 0}

        def responder(_payload):
            idx = min(call_count["n"], len(pages) - 1)
            call_count["n"] += 1
            return MessagesRes(messages=pages[idx])

        mock_transport.set_response(Opcode.MESSAGES, responder)

        result = await mock_transport.fetch_messages(
            chat_id=100,
            history_from=datetime(2026, 1, 1),
            history_to=datetime(2026, 1, 2),
            limit=50,
        )

        assert len(result) == 50
        message_calls = [s for s in mock_transport.sent if s[0] == Opcode.MESSAGES]
        assert len(message_calls) == 1

    async def test_limit_none_is_unbounded(self, mock_transport):
        """`limit=None` is the default and must preserve the pre-parameter behavior."""
        ts_from = int(datetime(2026, 1, 1).timestamp()) * 1000
        ts_to = int(datetime(2026, 1, 2).timestamp()) * 1000
        # Oldest-first as the server returns them.
        page = [_make_msg(i, ts_to - i * 1000) for i in range(10, 0, -1)]
        mock_transport.set_response(Opcode.MESSAGES, MessagesRes(messages=page))

        result = await mock_transport.fetch_messages(
            chat_id=100,
            history_from=datetime(2026, 1, 1),
            history_to=datetime(2026, 1, 2),
        )

        assert len(result) == 10

    async def test_limit_zero_returns_empty_without_request(self, mock_transport):
        """`limit<=0` is a degenerate case — the caller wants zero messages, so
        don't hit the API at all."""
        mock_transport.set_response(Opcode.MESSAGES, MessagesRes(messages=[]))

        result = await mock_transport.fetch_messages(
            chat_id=100,
            history_from=datetime(2026, 1, 1),
            history_to=datetime(2026, 1, 2),
            limit=0,
        )

        assert result == []
        assert [s for s in mock_transport.sent if s[0] == Opcode.MESSAGES] == []
