from enum import Enum


class Opcode(int, Enum):
    PING = 1
    INIT = 6
    PHONE_LOGIN = 17
    VERIFY_CODE = 18
    SYNC = 19
    CHAT_INFO = 48
    CONTACT_INFO = 32
    MESSAGES = 49
    FILE_URL = 88
    VIDEO_URL = 83
    SESSIONS_INFO = 96
    TWO_FACTOR_CHALLENGE = 115
    QR_LOGIN_INIT = 288
    QR_STATUS = 289
    QR_LOGIN = 291


class DeviceType(str, Enum):
    ANDROID = "ANDROID"
    IOS = "IOS"
    WEB = "WEB"
    DESKTOP = "DESKTOP"


class ChatType(str, Enum):
    DIALOG = "DIALOG"
    CHAT = "CHAT"
    CHANNEL = "CHANNEL"


class ContactNameType(str, Enum):
    ONEME = "ONEME"
    CUSTOM = "CUSTOM"


class AttachmentType(str, Enum):
    PHOTO = "PHOTO"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    FILE = "FILE"
    STICKER = "STICKER"
    CONTROL = "CONTROL"
    CONTACT = "CONTACT"
    CALL = "CALL"


class LinkType(str, Enum):
    FORWARD = "FORWARD"
    REPLY = "REPLY"


class AuthType(str, Enum):
    START_AUTH = "START_AUTH"
    CHECK_CODE = "CHECK_CODE"
