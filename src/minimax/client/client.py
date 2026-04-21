import asyncio
import inspect
import logging
import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime
from types import TracebackType
from typing import Any

from ..constants import PING_INTERVAL_SECONDS
from ..emitter import EventEmitter
from ..listeners import register_default_listeners
from pydantic import TypeAdapter

from ..schema import (
    OPCODE_SCHEMA,
    ApiError,
    Chat,
    Contact,
    DeviceType,
    EmptyPayload,
    ErrorRes,
    Event,
    Message,
    Opcode,
    Profile,
    UserAgent,
    UserSession,
    Wrapper,
)
from ..schema.responses import (
    LoginChallengeRes,
    LoginSuccessRes,
)
from .twofactor import TwoFactorFlow

log = logging.getLogger(__name__)


class Client(ABC):
    device_type: DeviceType

    def __init__(self, phone: int | None, token: str | None = None):
        self.phone = phone
        self.token = token
        self.me: Contact | None = None
        self.chats: list[Chat] = []
        self.contacts: list[Contact] = []

        self.events = EventEmitter()
        register_default_listeners(self)

        self._seq = 0
        self._pending: dict[int, asyncio.Future[Wrapper]] = {}
        self._recv_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._two_factor: TwoFactorFlow | None = None

    async def __aenter__(self):
        await self._connect()
        await self._start()
        log.info("Client connected")
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        await self._stop()
        await self._disconnect()
        log.info("Client disconnected")

    @staticmethod
    def build_wrapper(data: dict[str, Any]) -> Wrapper | None:
        """Validate opcode + payload via OPCODE_SCHEMA and build a Wrapper."""
        try:
            opcode = Opcode(data["opcode"])
        except ValueError:
            log.warning("Skipping unused opcode %d", data["opcode"])
            return None
        _, res_type = OPCODE_SCHEMA[opcode]
        payload = data.get("payload")
        if payload:
            if isinstance(payload, dict) and "error" in payload:
                parsed_payload = ErrorRes.model_validate(payload)
            elif isinstance(res_type, TypeAdapter):
                parsed_payload = res_type.validate_python(payload)
            else:
                parsed_payload = res_type.model_validate(payload)
        else:
            parsed_payload = EmptyPayload()
        return Wrapper(
            ver=data["ver"],
            cmd=data["cmd"],
            seq=data["seq"],
            opcode=opcode,
            payload=parsed_payload,
        )

    def handle_login(self, payload: LoginSuccessRes | LoginChallengeRes) -> None:
        """Handle a login response: emit SUCCESSFUL_LOGIN with token, or start 2FA flow if challenge is required."""
        if isinstance(payload, LoginChallengeRes):
            if self._two_factor:
                self._two_factor.cancel()
            self._two_factor = TwoFactorFlow(self, payload.password_challenge)
            self._two_factor.start()
            self.events.emit(Event.PASSWORD_CHALLENGE, payload.password_challenge)
        else:
            assert isinstance(payload, LoginSuccessRes)
            self._two_factor = None
            self.events.emit(Event.SUCCESSFUL_LOGIN, payload.token_attrs.login.token)

    def submit_twofactor_password(self, password: str) -> None:
        """Feed a 2FA password to the active challenge flow."""
        if not self._two_factor:
            raise ValueError("No active 2FA challenge")
        self._two_factor.submit_password(password)

    async def send_and_wait(self, opcode: Opcode, **kwargs: Any) -> Wrapper:
        future = await self._send(opcode, **kwargs)
        wrapper = await future
        if isinstance(wrapper.payload, ErrorRes):
            raise ApiError(wrapper.payload)
        return wrapper

    async def request(self, opcode: Opcode, **kwargs: Any):
        """Send a request and return the validated response payload."""
        wrapper = await self.send_and_wait(opcode, **kwargs)
        return wrapper.payload

    async def _start(self) -> None:
        """Start recv and ping loops, send INIT."""
        self._recv_task = asyncio.create_task(self._recv_loop())
        self._recv_task.add_done_callback(self.events.on_task_done)
        await self.request(
            Opcode.INIT,
            device_id=uuid.uuid4(),
            user_agent=UserAgent(device_type=self.device_type),
        )
        self._ping_task = asyncio.create_task(self._ping_loop())
        self._ping_task.add_done_callback(self.events.on_task_done)

    async def _stop(self) -> None:
        """Cancel tasks and pending futures."""
        if self._two_factor:
            self._two_factor.cancel()
        if self._ping_task:
            self._ping_task.cancel()
        if self._recv_task:
            self._recv_task.cancel()
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()

    async def _ping_loop(self) -> None:
        while True:
            await asyncio.sleep(PING_INTERVAL_SECONDS)
            await self._send(Opcode.PING)

    @abstractmethod
    async def _connect(self) -> None: ...

    @abstractmethod
    async def _disconnect(self) -> None: ...

    @abstractmethod
    async def _send(self, opcode: Opcode, **kwargs: Any) -> asyncio.Future[Wrapper]: ...

    @abstractmethod
    async def _recv_loop(self) -> None: ...

    @staticmethod
    async def _resolve_callback(result: Any) -> Any:
        """Await the result if it's a coroutine, otherwise return as-is."""
        if inspect.isawaitable(result):
            return await result
        return result

    async def _complete_login(
        self,
        payload: LoginSuccessRes | LoginChallengeRes,
        password_callback: Callable[[str], str | Awaitable[str]] | None = None,
    ) -> None:
        """Handle the login response: run 2FA loop if needed, then sync.

        Called by login_by_phone and login_by_qr after the initial auth step.
        """
        if isinstance(payload, LoginChallengeRes):
            if password_callback is None:
                raise ValueError("2FA required but no password_callback provided")
            track_id = str(payload.password_challenge.track_id)
            hint = payload.password_challenge.hint or ""
            while True:
                password = await self._resolve_callback(password_callback(hint))
                try:
                    payload = await self.request(
                        Opcode.TWO_FACTOR_CHALLENGE, track_id=track_id, password=password
                    )
                except ApiError as e:
                    log.error(e)
                    continue
                break

        assert isinstance(payload, LoginSuccessRes)
        await self.sync(payload.token_attrs.login.token)

    async def sync(self, token: str) -> None:
        """Authenticate with a token and sync chats/contacts."""
        log.info("Logging into %s", self.phone)
        res = await self.request(Opcode.SYNC, token=token)
        self.token = token
        self.me = res.profile.contact
        self.phone = res.profile.contact.phone
        self.chats = res.chats
        self.contacts = res.contacts
        log.info("Logged in, %d chats, %d contacts", len(res.chats), len(res.contacts))
        self.events.emit(Event.SUCCESSFUL_SYNC)

    async def get_chats(self, chat_ids: list[int]) -> list[Chat]:
        """Get chats by IDs. Checks cache first, fetches missing ones via CHAT_INFO."""
        known = {chat.id: chat for chat in self.chats}
        missing = [_id for _id in chat_ids if _id not in known]

        if missing:
            res = await self.request(Opcode.CHAT_INFO, chat_ids=missing)
            self.chats.extend(res.chats)
            for chat in res.chats:
                known[chat.id] = chat

        return [known[_id] for _id in chat_ids if _id in known]

    async def get_contacts(self, contact_ids: list[int]) -> list[Contact]:
        """Get contacts by IDs. Checks cache first, fetches missing ones via CONTACT_INFO."""
        known = {contact.id: contact for contact in self.contacts}
        missing = [_id for _id in contact_ids if _id not in known]

        if missing:
            res = await self.request(Opcode.CONTACT_INFO, contact_ids=missing)
            self.contacts.extend(res.contacts)
            for contact in res.contacts:
                known[contact.id] = contact

        return [known[_id] for _id in contact_ids if _id in known]

    async def get_sessions_info(self) -> list[UserSession]:
        """Get user sessions."""
        res = await self.request(Opcode.SESSIONS_INFO)
        return res.sessions

    async def get_file_url(self, file_id: int, chat_id: int, message_id: str) -> str:
        """Get download URL for a file attachment."""
        res = await self.request(Opcode.FILE_URL, file_id=file_id, chat_id=chat_id, message_id=message_id)
        return res.url

    async def get_video_url(self, video_id: int, chat_id: int, message_id: str, token: str) -> str:
        """Get the highest resolution download URL for a video attachment."""
        res = await self.request(
            Opcode.VIDEO_URL,
            video_id=video_id,
            chat_id=chat_id,
            message_id=message_id,
            token=token,
        )
        return res.get_url()

    async def fetch_messages(self, chat_id: int, history_from: datetime, history_to: datetime) -> list[Message]:
        """Fetch messages in a chat between history_from and history_to.

        The API only supports backward pagination from a message ID.
        We start from history_to and page backwards in steps of 100 until we reach history_from.
        """
        ts_from = int(history_from.timestamp()) * 1000
        ts_to = int(history_to.timestamp()) * 1000
        cursor = ts_to
        result: list[Message] = []

        while True:
            res = await self.request(
                Opcode.MESSAGES,
                chat_id=chat_id,
                from_=cursor,
                backward=100,
            )

            if not res.messages:
                break

            for msg in res.messages:
                if msg.time < ts_from:
                    break
                if msg.time <= ts_to:
                    result.append(msg)

            oldest = res.messages[-1]
            if oldest.time <= ts_from or len(res.messages) < 100:
                break

            cursor = int(oldest.id)

        return result
