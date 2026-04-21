"""Tests for TCP packet packing/unpacking."""

from minimax.client.tcp import HEADER_SIZE, pack, unpack
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


class TestUnpack:
    def test_roundtrip(self):
        wrapper = Wrapper(opcode=Opcode.PING, seq=1, payload=PingReq())
        data = pack(wrapper)
        results = unpack(data)
        assert len(results) == 1
        assert results[0].opcode == Opcode.PING
        assert results[0].seq == 1

    def test_short_data_returns_empty(self):
        assert unpack(b"short") == []

    def test_empty_data_returns_empty(self):
        assert unpack(b"") == []
