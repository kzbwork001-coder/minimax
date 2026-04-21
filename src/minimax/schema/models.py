from uuid import UUID

from pydantic import Field

from ..constants import APP_VERSION, DEVICE_LOCALE, DEVICE_NAME, LOCALE, OS_VERSION, SCREEN, TIMEZONE, USER_AGENT
from .enums import ChatType, ContactNameType, DeviceType, LinkType
from .interface import AnyAttachment, Attachment, BaseSchema


class Control(Attachment):
    event: str | None = Field(description="Event of the CONTROL attachment")
    message: str | None = Field(description="Message of the CONTROL attachment")
    short_message: str | None = Field(description="Short Message of the CONTROL attachment")


class Photo(Attachment):
    base_url: str = Field(description="Base URL of the photo")
    photo_id: int = Field(description="Photo ID")
    photo_token: str | None = Field(default=None, description="Photo token")
    height: int | None = Field(default=None, description="Height of the photo")
    width: int | None = Field(default=None, description="Width of the photo")


class Audio(Attachment):
    url: str = Field(description="Audio url")
    audio_id: int = Field(description="Audio ID")
    duration: int | None = Field(default=None, description="Duration of the audio")
    token: str | None = Field(default=None, description="Audio token")
    wave: str | None = Field(default=None, description="Audio wave")


class Video(Attachment):
    video_id: int = Field(description="Video ID")
    duration: int | None = Field(default=None, description="Duration of the video")
    height: int | None = Field(default=None, description="Height of the video")
    width: int | None = Field(default=None, description="Width of the video")
    token: str | None = Field(default=None, description="Video token")


class AttachmentContact(Attachment):
    contact_id: int = Field(description="Contact ID")
    first_name: str | None = Field(default=None, description="First name of the contact")
    photo_url: str | None = Field(default=None, description="Photo URL of the contact")


class File(Attachment):
    file_id: int = Field(description="File ID")
    name: str | None = Field(default=None, description="Name of the file")
    size: int | None = Field(default=None, description="Size of the file")
    token: str | None = Field(default=None, description="File token")


class Sticker(Attachment):
    sticker_id: int = Field(description="Sticker ID")
    url: str = Field(default=None, description="Sticker url")
    width: int | None = Field(default=None, description="Width of the sticker")


class Call(Attachment):
    """Sentinel for CALL attachment type (not modelled in minimax)."""
    pass


class Element(BaseSchema):
    type: str = Field(description="Type of the element")
    length: int = Field(description="Length of the element")
    from_: int | None = Field(default=None, alias="from", description="Start position of the element")


class Link(BaseSchema):
    type: LinkType = Field(description="Type of the link")
    message: "Message" = Field(description="Linked message")


class Message(BaseSchema):
    id: int = Field(description="ID of the message")
    sender: int = Field(description="Sender ID")
    text: str | None = Field(default=None, description="Text content of the message")
    time: int = Field(description="Timestamp of the message")
    type: str = Field(description="Type of the message")
    options: int | None = Field(default=None, description="Message options")
    elements: list[Element] = Field(default_factory=list, description="Formatting elements")
    attaches: list[AnyAttachment] = Field(default_factory=list, description="Attachments")
    link: Link | None = Field(default=None, description="Linked message")


class Chat(BaseSchema):
    cid: int | None = Field(default=None, description="Chat ID")
    id: int = Field(description="Chat ID")
    created: int = Field(description="Creation timestamp")
    type: ChatType = Field(description="Chat type")
    participants: dict[int, int] = Field(description="Participant IDs to timestamps")
    owner: int | None = Field(default=None, description="Owner ID, None for Channel")
    last_message: Message | None = Field(default=None, description="Last message in the chat")

    title: str | None = Field(default=None, description="Title of the chat")
    has_bots: bool = Field(default=False, description="Whether the chat has bots")
    join_time: int | None = Field(default=None, description="Join timestamp")
    last_delayed_update_time: int | None = Field(default=None, description="Last delayed update timestamp")
    last_event_time: int | None = Field(default=None, description="Last event timestamp")
    last_fire_delayed_error_time: int | None = Field(default=None, description="Last fire delayed error timestamp")
    modified: int | None = Field(default=None, description="Last modified timestamp")
    new_messages: int | None = Field(default=None, description="Number of new messages")
    options: dict | None = Field(default=None, description="Chat options")
    prev_message_id: int | None = Field(default=None, description="Previous message ID")
    restrictions: int | None = Field(default=None, description="Chat restrictions bitmask")
    status: str | None = Field(default=None, description="Chat status")


class UserSession(BaseSchema):
    client: str | None = Field(default=None, description="Client ID")
    info: str | None = Field(default=None, description="User info")
    location: str | None = Field(default=None, description="User location")
    time: int | None = Field(default=None, description="User time")
    current: bool = Field(default=False, description="Current status")


class UserAgent(BaseSchema):
    device_type: DeviceType = Field(description="Type of the device")
    app_version: str = Field(default=APP_VERSION, description="Version of the app")
    device_locale: str = Field(default=DEVICE_LOCALE, description="Locale of the device,")
    device_name: str = Field(default=DEVICE_NAME, description="Name of the device")
    header_user_agent: str = Field(default=USER_AGENT, description="User agent of the device")
    locale: str = Field(default=LOCALE, description="Locale of the device")
    os_version: str = Field(default=OS_VERSION, description="Version of the OS")
    screen: str = Field(default=SCREEN, description="Screen of the device")
    timezone: str = Field(default=TIMEZONE, description="Timezone of the device")


class ContactName(BaseSchema):
    name: str = Field(description="Full display name")
    type: ContactNameType = Field(description="Name type")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")


class Contact(BaseSchema):
    id: int = Field(description="Contact ID")
    account_status: int | None = Field(default=None, description="Account status")
    base_raw_url: str | None = Field(default=None, description="Base raw image URL")
    base_url: str | None = Field(default=None, description="Base image URL")
    names: list[ContactName] = Field(default_factory=list, description="Contact names")
    options: list[str] = Field(default_factory=list, description="Contact options")
    phone: int | None = Field(default=None, description="Phone number")
    photo_id: int | None = Field(default=None, description="Photo ID")
    registration_time: int | None = Field(default=None, description="Registration timestamp")
    status: str | None = Field(default=None, description="Contact status")
    update_time: int | None = Field(default=None, description="Last update timestamp")
    description: str | None = Field(default=None, description="Contact description")


class QrStatus(BaseSchema):
    expires_at: int = Field(description="Expiration timestamp")
    login_available: bool = Field(default=False, description="Whether login is available")


class Profile(BaseSchema):
    profile_options: list[int] = Field(default_factory=list, description="Profile options")
    contact: Contact = Field(description="Contact profile")


class TokenAttrs(BaseSchema):
    login: "TokenAttrsLogin" = Field(alias="LOGIN", description="LOGIN token attributes")

    class TokenAttrsLogin(BaseSchema):
        token: str = Field(description="TOKEN")


class PasswordChallenge(BaseSchema):
    track_id: UUID = Field(description="Track ID")
    config: "PasswordChallengeConfig" = Field(description="Password challenge config")
    hint: str | None = Field(default=None, description="Hint of the password")

    class PasswordChallengeConfig(BaseSchema):
        pass_min_len: int | None = Field(default=None, description="Minimum password length")
        pass_max_len: int | None = Field(default=None, description="Maximum password length")
        hint_max_len: int | None = Field(default=None, description="Maximum password length")
