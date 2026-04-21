import asyncio
import logging
from collections.abc import Awaitable, Callable

from ..schema import (
    ApiError,
    DeviceType,
    Opcode,
    PhoneLoginRes,
)
from .tcp import TcpTransport

log = logging.getLogger(__name__)


class SocketClient(TcpTransport):
    device_type = DeviceType.DESKTOP

    def __init__(self, phone: int | None, token: str | None = None):
        super().__init__(phone, token)
        self._verify_task: asyncio.Task | None = None

        # Bridge between verify_code() and _verify_flow(): codes are pushed
        # into the queue by verify_code() and consumed by the background task.
        # Supports multiple retry attempts within a single request_code() session.
        self._code_queue: asyncio.Queue[str] | None = None

    async def _disconnect(self) -> None:
        if self._verify_task:
            self._verify_task.cancel()
        await super()._disconnect()

    async def _verify_flow(self, phone_login_res: PhoneLoginRes) -> None:
        """Background task that waits for the code and completes phone login."""
        deadline = asyncio.get_running_loop().time() + phone_login_res.request_max_duration / 1000

        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError("Code verification timed out")

            try:
                code = await asyncio.wait_for(self._code_queue.get(), timeout=remaining)
            except asyncio.TimeoutError as e:
                raise TimeoutError("Code verification timed out") from e

            try:
                payload = await self.request(
                    Opcode.VERIFY_CODE,
                    token=phone_login_res.token,
                    verify_code=code,
                )
            except ApiError as e:
                log.error(e)
                continue

            self.handle_login(payload)
            return

    async def request_code(self) -> PhoneLoginRes:
        """Start the phone login flow.

        Sends PHONE_LOGIN and starts a background task waiting for verify_code().
        Returns PhoneLoginRes with code_length for the caller.
        """
        phone_login_res = await self.request(Opcode.PHONE_LOGIN, phone=self.phone)

        self._code_queue = asyncio.Queue()
        self._verify_task = asyncio.create_task(self._verify_flow(phone_login_res))  # type: ignore[call-arg]
        self._verify_task.add_done_callback(self.events.on_task_done)  # type: ignore[call-arg]

        return phone_login_res

    def verify_code(self, code: str) -> None:
        """Feed the code to the waiting verify flow."""
        if not self._verify_task or self._verify_task.done():
            raise ValueError("Code timed out or has not been requested")

        self._code_queue.put_nowait(code)

    async def login_by_phone(
        self,
        code_callback: Callable[[], str | Awaitable[str]],
        password_callback: Callable[[str], str | Awaitable[str]] | None = None,
    ) -> None:
        """High-level phone login: request code, prompt user, handle optional 2FA, sync.

        Retries code_callback on wrong SMS code, retries password_callback on wrong 2FA password.

        Args:
            code_callback: Called to obtain the SMS code. May be sync or async.
            password_callback: Called with the hint string when 2FA is required.
                               May be sync or async. If None and 2FA is needed, raises ValueError.
        """
        phone_login_res = await self.request(Opcode.PHONE_LOGIN, phone=self.phone)

        while True:
            code = await self._resolve_callback(code_callback())
            try:
                payload = await self.request(Opcode.VERIFY_CODE, token=phone_login_res.token, verify_code=code)
            except ApiError as e:
                log.error(e)
                continue
            break

        await self._complete_login(payload, password_callback)
