"""Integration tests for authentication flows (login, 2FA, errors)."""

from uuid import uuid4

import pytest

from minimax.schema import ApiError, Event, Opcode
from minimax.schema.interface import ErrorRes
from minimax.schema.models import Contact, ContactName, PasswordChallenge, Profile, TokenAttrs
from minimax.schema.responses import LoginChallengeRes, LoginSuccessRes


def _make_contact(cid: int, name: str = "User", phone: int = 71234567890) -> Contact:
    return Contact(
        id=cid,
        phone=phone,
        names=[ContactName(name=name, type="ONEME")],
        options=[],
    )


def _login_success() -> LoginSuccessRes:
    return LoginSuccessRes(
        profile=Profile(profile_options=[], contact=_make_contact(1)),
        token_attrs=TokenAttrs(LOGIN={"token": "issued_token"}),
    )


def _login_challenge() -> LoginChallengeRes:
    return LoginChallengeRes(
        password_challenge=PasswordChallenge(
            track_id=uuid4(),
            config=PasswordChallenge.PasswordChallengeConfig(),
            hint="your pet's name",
        )
    )


class TestHandleLogin:
    def test_success_emits_token(self, mock_transport):
        received: list[str] = []
        mock_transport.events.off(Event.SUCCESSFUL_LOGIN)  # drop default auto-sync
        mock_transport.events.on(Event.SUCCESSFUL_LOGIN, received.append)

        mock_transport.handle_login(_login_success())

        assert received == ["issued_token"]
        assert mock_transport._two_factor is None

    async def test_challenge_starts_two_factor(self, mock_transport):
        received: list[PasswordChallenge] = []
        mock_transport.events.on(Event.PASSWORD_CHALLENGE, received.append)

        mock_transport.handle_login(_login_challenge())

        assert mock_transport._two_factor is not None
        assert len(received) == 1
        assert received[0].hint == "your pet's name"

        mock_transport._two_factor.cancel()


class TestApiError:
    async def test_raises_on_error_response(self, mock_transport):
        mock_transport.set_response(
            Opcode.SYNC,
            ErrorRes(error="auth.invalid", message="Invalid token"),
        )

        with pytest.raises(ApiError) as exc_info:
            await mock_transport.sync("bad_token")

        assert exc_info.value.error_res.error == "auth.invalid"
        assert "Invalid token" in str(exc_info.value)


class TestTwoFactorFlow:
    def test_submit_without_active_flow_raises(self, mock_transport):
        with pytest.raises(ValueError, match="No active 2FA challenge"):
            mock_transport.submit_twofactor_password("secret")

    async def test_successful_password_completes_login(self, mock_transport):
        received: list[str] = []
        mock_transport.events.off(Event.SUCCESSFUL_LOGIN)
        mock_transport.events.on(Event.SUCCESSFUL_LOGIN, received.append)

        mock_transport.set_response(Opcode.TWO_FACTOR_CHALLENGE, _login_success())

        # Start 2FA flow
        mock_transport.handle_login(_login_challenge())
        assert mock_transport._two_factor is not None

        # Submit password and let the background task run
        mock_transport.submit_twofactor_password("correct_password")
        task = mock_transport._two_factor._task
        assert task is not None
        await task

        assert received == ["issued_token"]
