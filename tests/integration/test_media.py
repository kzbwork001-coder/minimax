"""Integration tests for media URL retrieval with mocked responses."""


from minimax.schema import Opcode
from minimax.schema.responses import FileUrlRes, VideoUrlRes


class TestFileUrl:
    async def test_get_file_url(self, mock_transport):
        mock_transport.set_response(
            Opcode.FILE_URL,
            FileUrlRes(url="https://example.com/file.zip", unsafe=False),
        )

        url = await mock_transport.get_file_url(file_id=10, chat_id=100, message_id=100)

        assert url == "https://example.com/file.zip"
        opcode, payload = mock_transport.sent[0]
        assert opcode == Opcode.FILE_URL
        assert payload.file_id == 10
        assert payload.chat_id == 100
        assert payload.message_id == 100


class TestVideoUrl:
    async def test_get_video_url_picks_best_resolution(self, mock_transport):
        mock_transport.set_response(
            Opcode.VIDEO_URL,
            VideoUrlRes(
                EXTERNAL="https://example.com/external.mp4",
                MP4_720="https://example.com/720.mp4",
                MP4_360="https://example.com/360.mp4",
            ),
        )

        url = await mock_transport.get_video_url(video_id=5, token="vtok")

        assert url == "https://example.com/720.mp4"
        opcode, payload = mock_transport.sent[0]
        assert opcode == Opcode.VIDEO_URL
        assert payload.video_id == 5
        assert payload.token == "vtok"

    async def test_get_video_url_fallback_external(self, mock_transport):
        mock_transport.set_response(
            Opcode.VIDEO_URL,
            VideoUrlRes(EXTERNAL="https://example.com/external.mp4"),
        )

        url = await mock_transport.get_video_url(video_id=5, token="vtok")

        assert url == "https://example.com/external.mp4"
