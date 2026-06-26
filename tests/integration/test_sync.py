"""Integration tests for the sync flow with mocked Max API responses."""

import pytest

from minimax.schema import ApiError, Opcode
from minimax.schema.interface import ErrorRes
from minimax.schema.models import Chat, Contact, ContactName, Profile
from minimax.schema.responses import (
    ChatInfoRes,
    ContactInfoByPhoneRes,
    ContactInfoRes,
    SessionInfoRes,
    SyncRes,
)


def _make_contact(cid: int, name: str = "User", phone: int = 71234567890) -> Contact:
    return Contact(
        id=cid,
        phone=phone,
        names=[ContactName(name=name, type="ONEME")],
        options=[],
    )


def _make_chat(chat_id: int, chat_type: str = "DIALOG") -> Chat:
    return Chat(id=chat_id, created=1700000000, type=chat_type, participants={1: 1700000000})


class TestSyncFlow:
    async def test_sync_populates_client_state(self, mock_transport):
        me = _make_contact(1, "Me")
        chats = [_make_chat(100), _make_chat(101, "CHAT")]
        contacts = [_make_contact(2, "Alice"), _make_contact(3, "Bob")]

        mock_transport.set_response(
            Opcode.SYNC,
            SyncRes(
                profile=Profile(profile_options=[], contact=me),
                chats=chats,
                contacts=contacts,
            ),
        )

        await mock_transport.sync("new_token")

        assert mock_transport.token == "new_token"
        assert mock_transport.me == me
        assert mock_transport.phone == me.phone
        assert len(mock_transport.chats) == 2
        assert len(mock_transport.contacts) == 2

    async def test_sync_sends_correct_token(self, mock_transport):
        me = _make_contact(1)
        mock_transport.set_response(
            Opcode.SYNC,
            SyncRes(profile=Profile(profile_options=[], contact=me), chats=[], contacts=[]),
        )

        await mock_transport.sync("the_token")

        assert mock_transport.sent[0][0] == Opcode.SYNC
        assert mock_transport.sent[0][1].token == "the_token"


class TestGetChats:
    async def test_get_chats_from_cache(self, mock_transport):
        mock_transport.chats = [_make_chat(100), _make_chat(101)]

        result = await mock_transport.get_chats([100, 101])

        assert len(result) == 2
        assert {c.id for c in result} == {100, 101}
        # Nothing was sent since cache was hit
        assert mock_transport.sent == []

    async def test_get_chats_fetches_missing(self, mock_transport):
        mock_transport.chats = [_make_chat(100)]
        mock_transport.set_response(
            Opcode.CHAT_INFO,
            ChatInfoRes(chats=[_make_chat(200), _make_chat(201)]),
        )

        result = await mock_transport.get_chats([100, 200, 201])

        assert len(result) == 3
        assert mock_transport.sent[0][0] == Opcode.CHAT_INFO
        assert mock_transport.sent[0][1].chat_ids == [200, 201]
        # Cache was updated
        assert len(mock_transport.chats) == 3


class TestGetContacts:
    async def test_get_contacts_from_cache(self, mock_transport):
        mock_transport.contacts = [_make_contact(1), _make_contact(2)]

        result = await mock_transport.get_contacts([1, 2])

        assert len(result) == 2
        assert mock_transport.sent == []

    async def test_get_contacts_fetches_missing(self, mock_transport):
        mock_transport.contacts = [_make_contact(1)]
        mock_transport.set_response(
            Opcode.CONTACT_INFO,
            ContactInfoRes(contacts=[_make_contact(50, "Dan")]),
        )

        result = await mock_transport.get_contacts([1, 50])

        assert len(result) == 2
        assert mock_transport.sent[0][0] == Opcode.CONTACT_INFO
        assert mock_transport.sent[0][1].contact_ids == [50]


class TestGetContactByPhone:
    async def test_returns_contact_and_sends_phone_as_string(self, mock_transport):
        contact = _make_contact(311877651, "Горец", phone=79991234567)
        mock_transport.set_response(
            Opcode.CONTACT_INFO_BY_PHONE,
            ContactInfoByPhoneRes(contact=contact),
        )

        result = await mock_transport.get_contact_by_phone(79991234567)

        assert result == contact
        assert mock_transport.sent[0][0] == Opcode.CONTACT_INFO_BY_PHONE
        # The request field is a str regardless of the int passed in.
        assert mock_transport.sent[0][1].phone == "79991234567"

    async def test_accepts_string_phone(self, mock_transport):
        contact = _make_contact(42, "Bob")
        mock_transport.set_response(
            Opcode.CONTACT_INFO_BY_PHONE,
            ContactInfoByPhoneRes(contact=contact),
        )

        await mock_transport.get_contact_by_phone("79991234567")

        assert mock_transport.sent[0][1].phone == "79991234567"

    async def test_caches_returned_contact(self, mock_transport):
        contact = _make_contact(42, "Bob")
        mock_transport.set_response(
            Opcode.CONTACT_INFO_BY_PHONE,
            ContactInfoByPhoneRes(contact=contact),
        )

        await mock_transport.get_contact_by_phone(79991234567)

        assert contact in mock_transport.contacts

    async def test_does_not_duplicate_cached_contact(self, mock_transport):
        existing = _make_contact(42, "Bob")
        mock_transport.contacts = [existing]
        mock_transport.set_response(
            Opcode.CONTACT_INFO_BY_PHONE,
            ContactInfoByPhoneRes(contact=_make_contact(42, "Bob")),
        )

        await mock_transport.get_contact_by_phone(79991234567)

        assert [c.id for c in mock_transport.contacts] == [42]

    async def test_raises_api_error_when_not_found(self, mock_transport):
        mock_transport.set_response(
            Opcode.CONTACT_INFO_BY_PHONE,
            ErrorRes(
                error="not.found",
                message="Cannot found contact by phone",
                localized_message="Not found",
                title="Not found",
            ),
        )

        with pytest.raises(ApiError) as exc_info:
            await mock_transport.get_contact_by_phone(70000000000)

        assert exc_info.value.error_res.error == "not.found"
        # A failed lookup must not pollute the contact cache.
        assert mock_transport.contacts == []


class TestSessionsInfo:
    async def test_returns_sessions(self, mock_transport):
        mock_transport.set_response(Opcode.SESSIONS_INFO, SessionInfoRes(sessions=[]))

        result = await mock_transport.get_sessions_info()

        assert result == []
        assert mock_transport.sent[0][0] == Opcode.SESSIONS_INFO
