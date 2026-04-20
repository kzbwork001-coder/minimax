from uuid import UUID

from pydantic import Field

from ..constants import CHATS_SYNC, CONTACTS_SYNC, DRAFT_SYNC, PRESENCE_SYNC, SYNC_CHAT_COUNT, SYNC_INTERACTIVE
from .enums import AuthType
from .interface import BaseReq
from .models import UserAgent


class UserAgentReq(BaseReq):
    """Payload for the user agent request."""

    device_id: UUID = Field(description="Device ID of the user agent")
    user_agent: UserAgent = Field(description="User agent of the user agent")


class PhoneLoginReq(BaseReq):
    """Payload for the code request."""

    phone: str = Field(description="Phone number of the user")
    type: AuthType = Field(default=AuthType.START_AUTH, description="Auth type of the user")
    language: str = Field(default="ru", description="Language of the user")


class VerifyCodeReq(BaseReq):
    """Payload for the use code request."""

    token: str = Field(description="Token of the user")
    verify_code: str = Field(description="Verify code of the user")
    auth_token_type: AuthType = Field(default=AuthType.CHECK_CODE, description="Auth type of the user")


class SyncReq(BaseReq):
    """Payload for the init request."""

    chat_count: int = Field(default=SYNC_CHAT_COUNT, description="Number of chats to initialize")
    chats_sync: int = Field(default=CHATS_SYNC, description="Chats to sync")
    contacts_sync: int = Field(default=CONTACTS_SYNC, description="Contacts to sync")
    presence_sync: int = Field(default=PRESENCE_SYNC, description="Presence to sync")
    interactive: bool = Field(default=SYNC_INTERACTIVE, description="Whether interactive is enabled")
    drafts_sync: int = Field(default=DRAFT_SYNC, description="Drafts to sync")
    token: str = Field(description="Token of the user")


class ChatInfoReq(BaseReq):
    """Payload for the chat info request."""

    chat_ids: list[int] = Field(default_factory=list, description="IDs of the chats")


class ContactInfoReq(BaseReq):
    """Payload for the contact info request."""

    contact_ids: list[int] = Field(default_factory=list, description="IDs of the contacts")


class PingReq(BaseReq):
    """Payload for the ping request."""

    interactive: bool = Field(default=SYNC_INTERACTIVE, description="Whether interactive is enabled")


class QrReq(BaseReq):
    """Payload for the ping qr status request."""

    track_id: str = Field(description="Track ID of the QR login")


class MessagesReq(BaseReq):
    """Payload for the message request."""

    chat_id: int = Field(description="ID of the chat")
    backward: int = Field(default=0, description="Number of messages to go back")
    forward: int = Field(default=0, description="Number of messages to go forward")
    from_: int = Field(alias="from", description="Message ID to start from")
    get_messages: bool = Field(default=True, description="Whether to get messages")


class FileUrlReq(BaseReq):
    """Payload for the file download request."""

    file_id: int = Field(description="ID of the file")
    chat_id: int = Field(description="ID of the chat")
    message_id: str = Field(description="ID of the message")


class VideoUrlReq(BaseReq):
    """Payload for the video download request."""

    video_id: int = Field(description="ID of the video")
    chat_id: int = Field(description="ID of the chat")
    message_id: str = Field(description="ID of the message")
    token: str = Field(description="Token of the video")


class TwoFactorReq(BaseReq):
    """Payload for the two factor request."""

    track_id: str = Field(description="Track ID of the two-factor login")
    password: str = Field(description="Password of the two-factor login")
