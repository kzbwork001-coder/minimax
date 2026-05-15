from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, ConfigDict, Discriminator, Field, SerializeAsAny, Tag, model_serializer, model_validator
from pydantic.alias_generators import to_camel

from ..constants import CMD, VER
from .enums import AttachmentType, Opcode

if TYPE_CHECKING:
    from .models import AttachmentContact, Audio, Call, Control, File, Photo, Sticker, Video


class BaseSchema(BaseModel):
    """Base model with camelCase alias generation for all schemas."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True)


class BasePayload(BaseSchema):
    """Base class for all payload types."""

    pass


class EmptyPayload(BasePayload):
    """Empty payload, replaces None in requests/responses that carry no data."""

    @model_validator(mode="before")
    @classmethod
    def _coerce_none(cls, data):
        """null in JSON → EmptyPayload"""
        if data is None:
            return {}
        return data

    @model_serializer
    def _serialize_to_none(self) -> None:
        """EmptyPayload → null in JSON output."""
        return None


class Wrapper(BaseSchema):
    """Wrapper for all request types."""

    cmd: int = Field(default=CMD, description="Always 0")
    opcode: Opcode = Field(description="Opcode of the request")
    seq: int = Field(description="Sequence number of the request for websocket")
    ver: int = Field(default=VER, description="Version of the request, always 11")
    payload: SerializeAsAny[BasePayload] = Field(default_factory=EmptyPayload, description="Payload of the request")


class BaseReq(BasePayload):
    """Base class for all request payloads."""

    pass


class BaseRes(BasePayload):
    """Base class for all response payloads."""

    pass


class ErrorRes(BasePayload):
    """Error payload that can replace any response at any time."""

    error: str = Field(description="Error message")
    localized_message: str | None = Field(default=None, description="Localized error message")
    message: str = Field(description="Error message")
    title: str | None = Field(default=None, description="Error title")


class ApiError(Exception):
    """Raised when the server responds with an ErrorRes."""

    def __init__(self, error_res: ErrorRes):
        self.error_res = error_res
        super().__init__(f"{error_res.error}: {error_res.title} — {error_res.message}")


class AccountNotFoundError(Exception):
    """Raised when a login response indicates the phone has no MAX account
    (server returned a REGISTER token instead of LOGIN + profile)."""

    def __init__(self, phone: int | None = None):
        self.phone = phone
        super().__init__(f"Missing MAX account for phone {phone}")


class Attachment(BaseSchema):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="allow")
    type: str = Field(alias="_type", description="Type of the attachment")


_ATTACHMENT_TAGS = {e.value for e in AttachmentType}


def _attachment_discriminator(data: Any) -> str:
    raw = data.get("_type", "") if isinstance(data, dict) else getattr(data, "type", "")
    return raw if raw in _ATTACHMENT_TAGS else "__unknown__"


AnyAttachment = Annotated[
    Annotated["Photo", Tag(AttachmentType.PHOTO)]
    | Annotated["Video", Tag(AttachmentType.VIDEO)]
    | Annotated["Audio", Tag(AttachmentType.AUDIO)]
    | Annotated["File", Tag(AttachmentType.FILE)]
    | Annotated["Sticker", Tag(AttachmentType.STICKER)]
    | Annotated["Control", Tag(AttachmentType.CONTROL)]
    | Annotated["AttachmentContact", Tag(AttachmentType.CONTACT)]
    | Annotated["Call", Tag(AttachmentType.CALL)]
    | Annotated[Attachment, Tag("__unknown__")],
    Discriminator(_attachment_discriminator),
]
