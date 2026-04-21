import logging
from asyncio import Task, sleep
from collections.abc import Awaitable, Callable

from ..schema import DeviceType, Opcode
from .ws import WsTransport

log = logging.getLogger(__name__)


class WebClient(WsTransport):
    device_type = DeviceType.WEB

    def __init__(self, phone: int | None, token: str | None = None):
        super().__init__(phone, token)
        self._qr_task: Task | None = None

    async def _disconnect(self) -> None:
        if self._qr_task:
            self._qr_task.cancel()
        await super()._disconnect()

    async def _qr_poll(self, track_id: str, interval: int) -> None:
        """Poll the QR status until successful. Emit QR_SUCCESSFUL_LOGIN event on success."""
        while True:
            await sleep(interval / 1000)
            status = await self.request(Opcode.QR_STATUS, track_id=track_id)

            if not status.status.login_available:
                continue

            payload = await self.request(Opcode.QR_LOGIN, track_id=track_id)

            self.handle_login(payload)
            return

    async def login_by_qr(
        self,
        qr_callback: Callable[[str], None | Awaitable[None]],
        password_callback: Callable[[str], str | Awaitable[str]] | None = None,
    ) -> None:
        """High-level QR login: show QR, wait for scan, handle optional 2FA, sync.

        Args:
            qr_callback: Called with the QR link string for the user to scan.
                          May be sync or async.
            password_callback: Called with the hint string when 2FA is required.
                               May be sync or async. If None and 2FA is needed, raises ValueError.
        """
        qr_init = await self.request(Opcode.QR_LOGIN_INIT)

        await self._resolve_callback(qr_callback(qr_init.qrLink))

        while True:
            await sleep(qr_init.polling_interval / 1000)
            status = await self.request(Opcode.QR_STATUS, track_id=qr_init.trackId)
            if status.status.login_available:
                break

        payload = await self.request(Opcode.QR_LOGIN, track_id=qr_init.trackId)
        await self._complete_login(payload, password_callback)
