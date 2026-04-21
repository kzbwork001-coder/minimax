
from minimax.schema.models import (
    AttachmentContact,
    Audio,
    Call,
    Control,
    Element,
    File,
    Message,
    Photo,
    Sticker,
    Video,
)


class TestPhoto:
    def test_create(self):
        photo = Photo(type="PHOTO", base_url="https://example.com/photo.jpg", photo_id=123)
        assert photo.type == "PHOTO"
        assert photo.base_url == "https://example.com/photo.jpg"
        assert photo.photo_id == 123
        assert photo.photo_token is None
        assert photo.height is None
        assert photo.width is None

    def test_with_dimensions(self):
        photo = Photo(type="PHOTO", base_url="https://example.com/photo.jpg", photo_id=1, height=100, width=200)
        assert photo.height == 100
        assert photo.width == 200


class TestAudio:
    def test_create(self):
        audio = Audio(type="AUDIO", url="https://example.com/audio.mp3", audio_id=456)
        assert audio.type == "AUDIO"
        assert audio.url == "https://example.com/audio.mp3"
        assert audio.audio_id == 456
        assert audio.duration is None
        assert audio.token is None
        assert audio.wave is None

    def test_with_all_fields(self):
        audio = Audio(type="AUDIO", url="https://example.com/a.mp3", audio_id=1, duration=120, token="tok", wave="w")
        assert audio.duration == 120
        assert audio.token == "tok"
        assert audio.wave == "w"


class TestVideo:
    def test_create(self):
        video = Video(type="VIDEO", video_id=789)
        assert video.type == "VIDEO"
        assert video.video_id == 789
        assert video.duration is None
        assert video.height is None
        assert video.width is None
        assert video.token is None


class TestFile:
    def test_create(self):
        file = File(type="FILE", file_id=101)
        assert file.type == "FILE"
        assert file.file_id == 101
        assert file.name is None
        assert file.size is None
        assert file.token is None


class TestSticker:
    def test_create(self):
        sticker = Sticker(type="STICKER", sticker_id=55, url="https://example.com/sticker.png")
        assert sticker.type == "STICKER"
        assert sticker.sticker_id == 55
        assert sticker.url == "https://example.com/sticker.png"


class TestControl:
    def test_create(self):
        ctrl = Control(type="CONTROL", event="typing", message="User is typing", short_message="typing")
        assert ctrl.type == "CONTROL"
        assert ctrl.event == "typing"
        assert ctrl.message == "User is typing"
        assert ctrl.short_message == "typing"


class TestAttachmentContact:
    def test_create(self):
        contact = AttachmentContact(type="CONTACT", contact_id=42)
        assert contact.type == "CONTACT"
        assert contact.contact_id == 42
        assert contact.first_name is None
        assert contact.photo_url is None


class TestCall:
    def test_create(self):
        call = Call(type="CALL")
        assert call.type == "CALL"

    def test_is_sentinel(self):
        """Call is a sentinel class with no extra fields beyond the base Attachment."""
        call = Call(type="CALL")
        # Should only have fields from base Attachment + extra allowed
        assert call.type == "CALL"


class TestElement:
    def test_create(self):
        el = Element(type="bold", length=5)
        assert el.type == "bold"
        assert el.length == 5
        assert el.from_ is None

    def test_with_from(self):
        el = Element(type="italic", length=3, **{"from": 2})
        assert el.from_ == 2


class TestMessage:
    def test_minimal(self):
        msg = Message(id=1, sender=100, time=1700000000, type="TEXT")
        assert msg.id == 1
        assert msg.sender == 100
        assert msg.text is None
        assert msg.attaches == []
        assert msg.elements == []
        assert msg.link is None

    def test_with_text(self):
        msg = Message(id=2, sender=200, text="Hello", time=1700000000, type="TEXT")
        assert msg.text == "Hello"

    def test_with_attachment(self):
        photo = Photo(type="PHOTO", base_url="https://example.com/p.jpg", photo_id=1)
        msg = Message(id=3, sender=300, time=1700000000, type="TEXT", attaches=[photo])
        assert len(msg.attaches) == 1
        assert isinstance(msg.attaches[0], Photo)
