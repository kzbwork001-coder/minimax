import asyncio
import logging
from typing import TYPE_CHECKING

from ..schema import ApiError, Opcode
from ..schema.models import PasswordChallenge

if TYPE_CHECKING:
    from .client import Client

log = logging.getLogger(__name__)


class TwoFactorFlow:
    def __init__(self, client: "Client", challenge: PasswordChallenge):
        self._client = client
        self._track_id = str(challenge.track_id)
        self._password_queue: asyncio.Queue[str] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())
        self._task.add_done_callback(self._client.events.on_task_done)

    def cancel(self) -> None:
        if self._task:
            self._task.cancel()

    def submit_password(self, password: str) -> None:
        self._password_queue.put_nowait(password)

    async def _run(self) -> None:
        while True:
            password = await self._password_queue.get()

            try:
                payload = await self._client.request(
                    Opcode.TWO_FACTOR_CHALLENGE,
                    track_id=self._track_id,
                    password=password,
                )
            except ApiError as e:
                log.error(e)
                continue

            self._client.handle_login(payload)
            return
