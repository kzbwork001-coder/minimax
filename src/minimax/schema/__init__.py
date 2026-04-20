from pydantic import TypeAdapter

from .enums import AttachmentType as AttachmentType
from .enums import AuthType as AuthType
from .enums import ChatType as ChatType
from .enums import ContactNameType as ContactNameType
from .enums import DeviceType as DeviceType
from .enums import LinkType as LinkType
from .enums import Opcode as Opcode
from .events import Event as Event
from .interface import AnyAttachment as AnyAttachment
from .interface import ApiError as ApiError
from .interface import Attachment as Attachment
from .interface import BasePayload as BasePayload
from .interface import BaseReq as BaseReq
from .interface import BaseRes as BaseRes
from .interface import BaseSchema as BaseSchema
from .interface import EmptyPayload as EmptyPayload
from .interface import ErrorRes as ErrorRes
from .interface import Wrapper as Wrapper
from .models import AttachmentContact as AttachmentContact
from .models import Audio as Audio
from .models import Call as Call
from .models import Chat as Chat
from .models import Contact as Contact
from .models import ContactName as ContactName
from .models import Control as Control
from .models import Element as Element
from .models import File as File
from .models import Link as Link
from .models import Message as Message
from .models import PasswordChallenge as PasswordChallenge
from .models import Photo as Photo
from .models import Profile as Profile
from .models import QrStatus as QrStatus
from .models import Sticker as Sticker
from .models import TokenAttrs as TokenAttrs
from .models import UserAgent as UserAgent
from .models import UserSession as UserSession
from .models import Video as Video
from .requests import ChatInfoReq as ChatInfoReq
from .requests import ContactInfoReq as ContactInfoReq
from .requests import FileUrlReq as FileUrlReq
from .requests import MessagesReq as MessagesReq
from .requests import PhoneLoginReq as PhoneLoginReq
from .requests import PingReq as PingReq
from .requests import QrReq as QrReq
from .requests import SyncReq as SyncReq
from .requests import TwoFactorReq as TwoFactorReq
from .requests import UserAgentReq as UserAgentReq
from .requests import VerifyCodeReq as VerifyCodeReq
from .requests import VideoUrlReq as VideoUrlReq
from .responses import ChatInfoRes as ChatInfoRes
from .responses import ContactInfoRes as ContactInfoRes
from .responses import FileUrlRes as FileUrlRes
from .responses import LoginRes as LoginRes
from .responses import MessagesRes as MessagesRes
from .responses import PhoneLoginRes as PhoneLoginRes
from .responses import QrLoginInitRes as QrLoginInitRes
from .responses import QrStatusRes as QrStatusRes
from .responses import SessionInfoRes as SessionInfoRes
from .responses import SyncRes as SyncRes
from .responses import UserAgentRes as UserAgentRes
from .responses import VideoUrlRes as VideoUrlRes

Message.model_rebuild()

OPCODE_SCHEMA: dict[Opcode, tuple[type[BaseReq] | type[EmptyPayload], type[BaseRes] | type[EmptyPayload] | TypeAdapter]] = {
    Opcode.PING: (PingReq, EmptyPayload),
    Opcode.SYNC: (SyncReq, SyncRes),
    Opcode.PHONE_LOGIN: (PhoneLoginReq, PhoneLoginRes),
    Opcode.VERIFY_CODE: (VerifyCodeReq, LoginRes),
    Opcode.TWO_FACTOR_CHALLENGE: (TwoFactorReq, LoginRes),
    Opcode.INIT: (UserAgentReq, UserAgentRes),
    Opcode.CHAT_INFO: (ChatInfoReq, ChatInfoRes),
    Opcode.CONTACT_INFO: (ContactInfoReq, ContactInfoRes),
    Opcode.QR_LOGIN_INIT: (EmptyPayload, QrLoginInitRes),
    Opcode.QR_STATUS: (QrReq, QrStatusRes),
    Opcode.QR_LOGIN: (QrReq, LoginRes),
    Opcode.MESSAGES: (MessagesReq, MessagesRes),
    Opcode.FILE_URL: (FileUrlReq, FileUrlRes),
    Opcode.VIDEO_URL: (VideoUrlReq, VideoUrlRes),
    Opcode.SESSIONS_INFO: (EmptyPayload, SessionInfoRes),
}
