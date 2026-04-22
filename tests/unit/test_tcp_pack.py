"""Tests for TCP packet packing/unpacking."""

import msgpack

from minimax.client.tcp import HEADER_SIZE, pack, unpack_items
from minimax.schema import Opcode, Wrapper
from minimax.schema.requests import PingReq


class TestPack:
    def test_pack_produces_bytes(self):
        wrapper = Wrapper(opcode=Opcode.PING, seq=1, payload=PingReq())
        data = pack(wrapper)
        assert isinstance(data, bytes)
        assert len(data) > HEADER_SIZE

    def test_header_fields(self):
        wrapper = Wrapper(opcode=Opcode.PING, seq=5, payload=PingReq())
        data = pack(wrapper)
        # ver = 11
        assert data[0] == 11
        # cmd = 0 (2 bytes)
        assert int.from_bytes(data[1:3]) == 0
        # seq = 5 % 256 = 5
        assert data[3] == 5
        # opcode = 1 (PING)
        assert int.from_bytes(data[4:6]) == 1

    def test_seq_wraps_at_256(self):
        wrapper = Wrapper(opcode=Opcode.PING, seq=300, payload=PingReq())
        data = pack(wrapper)
        assert data[3] == 300 % 256


class TestUnpackItems:
    def test_returns_raw_header_and_payload_dict(self):
        """`unpack_items` exposes the pre-validation dicts so recv loops can
        decide how to handle per-item validation failures (e.g., fail the
        specific pending future for that seq instead of dropping the packet)."""
        wrapper = Wrapper(opcode=Opcode.PING, seq=42, payload=PingReq())
        data = pack(wrapper)

        items = unpack_items(data)

        assert len(items) == 1
        assert items[0]["seq"] == 42
        assert items[0]["opcode"] == Opcode.PING.value

    def test_batched_list_payload_yields_one_item_per_entry(self):
        """The server batches responses by wrapping the payload in a list; each
        list element must become its own item dict so they can be dispatched
        independently."""
        raw = _build_raw_packet_list(
            seq=7,
            opcode=Opcode.PING.value,
            payloads=[{"a": 1}, {"b": 2}, {"c": 3}],
        )

        items = unpack_items(raw)

        assert len(items) == 3
        assert [item["payload"] for item in items] == [{"a": 1}, {"b": 2}, {"c": 3}]
        # Header values are propagated to every item.
        assert all(item["seq"] == 7 for item in items)

    def test_short_data_returns_empty(self):
        assert unpack_items(b"") == []
        assert unpack_items(b"short") == []


def _build_raw_packet(seq: int, opcode: int, payload: dict | None) -> bytes:
    """Assemble a valid minimax TCP packet with an uncompressed msgpack payload."""
    payload_bytes = msgpack.packb(payload) if payload is not None else b""
    header = (
        (11).to_bytes(1, "big")
        + (0).to_bytes(2, "big")
        + (seq % 256).to_bytes(1, "big")
        + opcode.to_bytes(2, "big")
        + len(payload_bytes).to_bytes(4, "big")
    )
    return header + payload_bytes


def _build_raw_packet_list(seq: int, opcode: int, payloads: list[dict]) -> bytes:
    """Assemble a batched packet whose msgpack payload is a list."""
    return _build_raw_packet(seq=seq, opcode=opcode, payload=payloads)  # type: ignore[arg-type]
