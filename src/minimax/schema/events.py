from enum import Enum


class Event(str, Enum):
    # Fired when any login flow obtains a token from the server.
    # Default listener triggers sync()
    # Listener signature: (token: str) -> None
    SUCCESSFUL_LOGIN = "successful_login"

    # Fired when the server requires a 2FA password challenge.
    # No default listener. The 2FA flow is handled by TwoFactorFlow internally.
    # Listener signature: (challenge: PasswordChallenge) -> None
    PASSWORD_CHALLENGE = "password_challenge"

    # Fired after sync() completes — the client is fully authenticated and synced.
    # Do not have default listener.
    # Listener signature: () -> None
    SUCCESSFUL_SYNC = "successful_sync"

    # Fired when an error occurs in any background task (recv loop, ping loop, QR polling, verify flow).
    # By default, emitted in EventEmitter.on_task_done
    # Default listener just log the error message
    # Listener signature: (error: ErrorRes | Exception) -> None
    BACKGROUND_TASK_ERROR = "background_task_error"
