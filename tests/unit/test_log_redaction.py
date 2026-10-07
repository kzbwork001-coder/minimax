import logging

from minimax.client.tcp import pack
from minimax.log import REDACTED, Redacted, redact
from minimax.schema import Opcode, Wrapper
from minimax.schema.requests import SyncReq

SECRET = "An_auth.key-123"


def test_redact_masks_nested_token_and_password():
    payload = {
        "tokenAttrs": {"LOGIN": {"token": SECRET}},
        "password": "hunter2",
        "authTokenType": "CHECK_CODE",
        "chatId": 1,
    }

    assert redact(payload) == {
        "tokenAttrs": {"LOGIN": {"token": REDACTED}},
        "password": REDACTED,
        "authTokenType": "CHECK_CODE",
        "chatId": 1,
    }


def test_redacted_json_frame_hides_token():
    frame = Wrapper(opcode=Opcode.SYNC, seq=1, payload=SyncReq(token=SECRET)).to_json()

    rendered = str(Redacted(frame))

    assert SECRET not in rendered
    assert '"token": "***"' in rendered


def test_redacted_model_hides_token():
    assert SECRET not in str(Redacted(SyncReq(token=SECRET)))


def test_redacted_non_json_string_is_not_echoed():
    assert str(Redacted(f"garbage {SECRET}")) == f"<{len('garbage ' + SECRET)} unparsed chars>"


def test_tcp_pack_debug_log_hides_token(caplog):
    with caplog.at_level(logging.DEBUG, logger="minimax.client.tcp"):
        pack(Wrapper(opcode=Opcode.SYNC, seq=1, payload=SyncReq(token=SECRET)))

    assert "pack: seq=1 opcode=SYNC" in caplog.text
    assert SECRET not in caplog.text
