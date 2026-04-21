"""Tests for attachment type discrimination (AnyAttachment union parsing)."""

from pydantic import TypeAdapter

from minimax.schema.interface import AnyAttachment, Attachment
from minimax.schema.models import (
    AttachmentContact,
    Audio,
    Call,
    Control,
    File,
    Photo,
    Sticker,
    Video,
)

adapter = TypeAdapter(AnyAttachment)


class TestAttachmentDiscriminator:
    def test_photo(self):
        data = {"_type": "PHOTO", "baseUrl": "https://example.com/p.jpg", "photoId": 1}
        result = adapter.validate_python(data)
        assert isinstance(result, Photo)
        assert result.base_url == "https://example.com/p.jpg"
        assert result.photo_id == 1

    def test_video(self):
        data = {"_type": "VIDEO", "videoId": 10}
        result = adapter.validate_python(data)
        assert isinstance(result, Video)
        assert result.video_id == 10

    def test_audio(self):
        data = {"_type": "AUDIO", "url": "https://example.com/a.mp3", "audioId": 5}
        result = adapter.validate_python(data)
        assert isinstance(result, Audio)
        assert result.audio_id == 5

    def test_file(self):
        data = {"_type": "FILE", "fileId": 20}
        result = adapter.validate_python(data)
        assert isinstance(result, File)
        assert result.file_id == 20

    def test_sticker(self):
        data = {"_type": "STICKER", "stickerId": 3, "url": "https://example.com/s.png"}
        result = adapter.validate_python(data)
        assert isinstance(result, Sticker)
        assert result.sticker_id == 3

    def test_control(self):
        data = {"_type": "CONTROL", "event": "typing", "message": "msg", "shortMessage": "s"}
        result = adapter.validate_python(data)
        assert isinstance(result, Control)
        assert result.event == "typing"

    def test_contact(self):
        data = {"_type": "CONTACT", "contactId": 99}
        result = adapter.validate_python(data)
        assert isinstance(result, AttachmentContact)
        assert result.contact_id == 99

    def test_call(self):
        data = {"_type": "CALL"}
        result = adapter.validate_python(data)
        assert isinstance(result, Call)
        assert result.type == "CALL"

    def test_unknown_type_falls_back_to_base(self):
        data = {"_type": "UNKNOWN_FUTURE_TYPE", "someField": "value"}
        result = adapter.validate_python(data)
        assert isinstance(result, Attachment)
        assert not isinstance(result, Photo)
        assert result.type == "UNKNOWN_FUTURE_TYPE"

    def test_empty_type_falls_back_to_base(self):
        data = {"_type": ""}
        result = adapter.validate_python(data)
        assert isinstance(result, Attachment)
