from minimax.schema.enums import AttachmentType, ChatType, ContactNameType, DeviceType, LinkType, Opcode


class TestAttachmentType:
    def test_values(self):
        assert AttachmentType.PHOTO == "PHOTO"
        assert AttachmentType.VIDEO == "VIDEO"
        assert AttachmentType.AUDIO == "AUDIO"
        assert AttachmentType.FILE == "FILE"
        assert AttachmentType.STICKER == "STICKER"
        assert AttachmentType.CONTROL == "CONTROL"
        assert AttachmentType.CONTACT == "CONTACT"
        assert AttachmentType.CALL == "CALL"

    def test_is_str_enum(self):
        assert isinstance(AttachmentType.PHOTO, str)

    def test_all_members(self):
        assert len(AttachmentType) == 8


class TestChatType:
    def test_values(self):
        assert ChatType.DIALOG == "DIALOG"
        assert ChatType.CHAT == "CHAT"
        assert ChatType.CHANNEL == "CHANNEL"


class TestDeviceType:
    def test_values(self):
        assert DeviceType.ANDROID == "ANDROID"
        assert DeviceType.IOS == "IOS"
        assert DeviceType.WEB == "WEB"
        assert DeviceType.DESKTOP == "DESKTOP"


class TestLinkType:
    def test_values(self):
        assert LinkType.FORWARD == "FORWARD"
        assert LinkType.REPLY == "REPLY"


class TestContactNameType:
    def test_values(self):
        assert ContactNameType.ONEME == "ONEME"
        assert ContactNameType.CUSTOM == "CUSTOM"


class TestOpcode:
    def test_is_int_enum(self):
        assert isinstance(Opcode.PING, int)
        assert Opcode.PING == 1
        assert Opcode.SYNC == 19
