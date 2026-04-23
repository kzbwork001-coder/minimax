from typing import Annotated, Any

from pydantic import Discriminator, Field, Tag, TypeAdapter

from .interface import BaseRes
from .models import Chat, Contact, Message, PasswordChallenge, Profile, QrStatus, TokenAttrs, UserSession


class UserAgentRes(BaseRes):
    """Payload for the user agent response."""

    location: str = Field(description="Location of the user agent")
    reg_country_code: list[str] = Field(
        default_factory=list,
        alias="reg-country-code",
        description="Country codes of the request",
    )
    phone_auth_enabled: bool = Field(
        default=True,
        alias="phone-auth-enabled",
        description="Whether phone authentication is enabled",
    )


class PhoneLoginRes(BaseRes):
    """Payload for the code request."""

    token: str = Field(default=None, description="Token of the code")
    code_length: int = Field(default=None, description="Length of the code")
    request_max_duration: int = Field(default=None, description="Maximum duration of the request")


class SyncRes(BaseRes):
    """Payload for the sync response."""

    chats: list[Chat] = Field(default_factory=list, description="Chats after sync")
    contacts: list[Contact] = Field(default_factory=list, description="Contacts after sync")
    profile: Profile = Field(description="Profile after sync")
    time: int | None = Field(default=None, description="Last update timestamp")
    video_chat_history: bool = Field(default=False, description="Video chat history")


class ChatInfoRes(BaseRes):
    """Payload for the chat info response."""

    chats: list[Chat] = Field(default_factory=list, description="Chats after sync")


class ContactInfoRes(BaseRes):
    """Payload for the contact info response."""

    contacts: list[Contact] = Field(default_factory=list, description="Contacts after sync")


class SessionInfoRes(BaseRes):
    """Payload for the session info response."""

    sessions: list[UserSession] = Field(default_factory=list, description="Sessions after sync")


class QrLoginInitRes(BaseRes):
    """Payload for the qr login response."""

    expires_at: int = Field(description="Expiration timestamp")
    polling_interval: int = Field(description="Polling interval")
    qrLink: str = Field(description="QR login URL")
    trackId: str = Field(description="Track ID")
    ttl: int | None = Field(default=None, description="TTL")


class QrStatusRes(BaseRes):
    """Payload for the ping qr status response."""

    status: QrStatus = Field(description="Status of the QR login")


class LoginSuccessRes(BaseRes):
    """Login response when authentication succeeds (no 2FA or 2FA already passed)."""

    profile: Profile = Field(description="Profile after sync")
    token_attrs: TokenAttrs = Field(description="Token attributes")


class LoginChallengeRes(BaseRes):
    """Login response when 2FA is required."""

    password_challenge: PasswordChallenge = Field(description="Password challenge")


def _login_res_discriminator(data: Any) -> str:
    if isinstance(data, dict):
        return "challenge" if "passwordChallenge" in data else "success"
    return "challenge" if isinstance(data, LoginChallengeRes) else "success"


LoginRes = TypeAdapter(
    Annotated[
        Annotated[LoginSuccessRes, Tag("success")] | Annotated[LoginChallengeRes, Tag("challenge")],
        Discriminator(_login_res_discriminator),
    ]
)


class MessagesRes(BaseRes):
    """Payload for the message response."""

    messages: list[Message] = Field(default_factory=list, description="Messages after sync")


class FileUrlRes(BaseRes):
    """Payload for the file download response."""

    url: str = Field(description="URL of the file")
    unsafe: bool = Field(default=False, description="Whether the file is unsafe")


class VideoUrlRes(BaseRes):
    """Payload for the video download response."""

    external: str = Field(alias="EXTERNAL", description="External URL of the video")
    cache: bool = Field(default=False, description="Whether the video is cached")
    mp4_16: str | None = Field(default=None, alias="MP4_16", description="URL of the 16p MP4 video")
    mp4_32: str | None = Field(default=None, alias="MP4_32", description="URL of the 32p MP4 video")
    mp4_64: str | None = Field(default=None, alias="MP4_64", description="URL of the 64p MP4 video")
    mp4_144: str | None = Field(default=None, alias="MP4_144", description="URL of the 144p MP4 video")
    mp4_240: str | None = Field(default=None, alias="MP4_240", description="URL of the 240p MP4 video")
    mp4_360: str | None = Field(default=None, alias="MP4_360", description="URL of the 360p MP4 video")
    mp4_480: str | None = Field(default=None, alias="MP4_480", description="URL of the 480p MP4 video")
    mp4_720: str | None = Field(default=None, alias="MP4_720", description="URL of the 720p MP4 video")
    mp4_1080: str | None = Field(default=None, alias="MP4_1080", description="URL of the 1080p MP4 video")
    mp4_1440: str | None = Field(default=None, alias="MP4_1440", description="URL of the 1440p MP4 video")
    mp4_2160: str | None = Field(default=None, alias="MP4_2160", description="URL of the 2160p MP4 video")
    mp4_4320: str | None = Field(default=None, alias="MP4_4320", description="URL of the 4320p MP4 video")
    mp4_8640: str | None = Field(default=None, alias="MP4_8640", description="URL of the 8640p MP4 video")

    _resolutions = [
        "mp4_8640",
        "mp4_4320",
        "mp4_2160",
        "mp4_1440",
        "mp4_1080",
        "mp4_720",
        "mp4_480",
        "mp4_360",
        "mp4_240",
        "mp4_144",
        "mp4_64",
        "mp4_32",
        "mp4_16",
    ]

    def get_url(self) -> str:
        """Get the URL of the highest available resolution, falls back to external."""
        for res in self._resolutions:
            url = getattr(self, res)
            if url:
                return url
        return self.external
