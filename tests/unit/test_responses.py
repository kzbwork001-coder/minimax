"""Tests for response model validation."""

from minimax.schema.responses import (
    FileUrlRes,
    LoginChallengeRes,
    LoginRes,
    LoginSuccessRes,
    VideoUrlRes,
)


class TestVideoUrlRes:
    def test_get_url_highest_resolution(self):
        res = VideoUrlRes(
            EXTERNAL="https://example.com/external.mp4",
            MP4_720="https://example.com/720.mp4",
            MP4_360="https://example.com/360.mp4",
        )
        assert res.get_url() == "https://example.com/720.mp4"

    def test_get_url_fallback_to_external(self):
        res = VideoUrlRes(EXTERNAL="https://example.com/external.mp4")
        assert res.get_url() == "https://example.com/external.mp4"

    def test_get_url_picks_highest_available(self):
        res = VideoUrlRes(
            EXTERNAL="https://example.com/ext.mp4",
            MP4_1080="https://example.com/1080.mp4",
            MP4_480="https://example.com/480.mp4",
        )
        assert res.get_url() == "https://example.com/1080.mp4"


class TestFileUrlRes:
    def test_create(self):
        res = FileUrlRes(url="https://example.com/file.zip", unsafe=False)
        assert res.url == "https://example.com/file.zip"
        assert res.unsafe is False


class TestLoginRes:
    def test_discriminates_success(self):
        data = {
            "profile": {
                "profileOptions": [],
                "contact": {"id": 1, "names": [], "options": []},
            },
            "tokenAttrs": {"LOGIN": {"token": "abc123"}},
        }
        result = LoginRes.validate_python(data)
        assert isinstance(result, LoginSuccessRes)
        assert result.token_attrs.login.token == "abc123"

    def test_discriminates_challenge(self):
        data = {
            "passwordChallenge": {
                "trackId": "550e8400-e29b-41d4-a716-446655440000",
                "config": {},
            }
        }
        result = LoginRes.validate_python(data)
        assert isinstance(result, LoginChallengeRes)
        assert str(result.password_challenge.track_id) == "550e8400-e29b-41d4-a716-446655440000"
