"""Tests for model serialization (to_json / model_dump)."""

import json

from minimax.schema.interface import Wrapper, EmptyPayload
from minimax.schema.enums import Opcode
from minimax.schema.models import Photo, Call
from minimax.schema.requests import PingReq, SyncReq


class TestWrapperSerialization:
    def test_to_json(self):
        wrapper = Wrapper(opcode=Opcode.PING, seq=1, payload=PingReq())
        raw = wrapper.to_json()
        data = json.loads(raw)
        assert data["opcode"] == 1
        assert data["seq"] == 1
        assert data["ver"] == 11
        assert data["cmd"] == 0
        assert data["payload"]["interactive"] is True

    def test_empty_payload_serializes_to_null(self):
        wrapper = Wrapper(opcode=Opcode.PING, seq=2, payload=EmptyPayload())
        raw = wrapper.to_json()
        data = json.loads(raw)
        assert data["payload"] is None


class TestAttachmentSerialization:
    def test_photo_dump_by_alias(self):
        photo = Photo(type="PHOTO", base_url="https://example.com/p.jpg", photo_id=1, height=100, width=200)
        data = photo.model_dump(by_alias=True)
        assert data["_type"] == "PHOTO"
        assert data["baseUrl"] == "https://example.com/p.jpg"
        assert data["photoId"] == 1
        assert data["height"] == 100
        assert data["width"] == 200

    def test_call_dump_by_alias(self):
        call = Call(type="CALL")
        data = call.model_dump(by_alias=True)
        assert data["_type"] == "CALL"

    def test_photo_to_json(self):
        photo = Photo(type="PHOTO", base_url="https://example.com/p.jpg", photo_id=1)
        raw = photo.to_json()
        data = json.loads(raw)
        assert data["_type"] == "PHOTO"
        assert data["baseUrl"] == "https://example.com/p.jpg"


class TestRequestSerialization:
    def test_sync_req_camel_case(self):
        req = SyncReq(token="test_token")
        data = req.model_dump(by_alias=True)
        assert data["token"] == "test_token"
        assert "chatCount" in data
        assert "contactsSync" in data

    def test_ping_req(self):
        req = PingReq()
        data = req.model_dump(by_alias=True)
        assert data["interactive"] is True
