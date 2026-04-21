"""Shared fixtures and mock transport for integration tests."""

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from minimax.client.client import Client
from minimax.schema import (
    OPCODE_SCHEMA,
    DeviceType,
    EmptyPayload,
    Opcode,
    Wrapper,
)


class MockTransport(Client):
    """In-memory transport that resolves requests with pre-configured responses.

    Simulates the Max API without opening real sockets — tests register responses
    per-opcode and the mock validates outgoing payloads + immediately fulfils
    the awaiting future with the registered response.
    """

    device_type = DeviceType.WEB

    def __init__(self, phone: int | None = None, token: str | None = None):
        super().__init__(phone, token)
        self._responses: dict[Opcode, Any | Callable[..., Any]] = {}
        self.sent: list[tuple[Opcode, Any]] = []

    def set_response(self, opcode: Opcode, payload: Any) -> None:
        """Register a payload (or callable) to return for a given opcode."""
        self._responses[opcode] = payload

    async def _connect(self) -> None:
        pass

    async def _disconnect(self) -> None:
        pass

    async def _recv_loop(self) -> None:
        # No-op: _send resolves futures synchronously from the mock table
        await asyncio.Event().wait()

    async def _send(self, opcode: Opcode, **kwargs: Any) -> asyncio.Future[Wrapper]:
        self._seq += 1
        seq = self._seq

        req_type, _ = OPCODE_SCHEMA[opcode]
        payload_model = req_type(**kwargs)  # type: ignore[call-arg]
        self.sent.append((opcode, payload_model))

        future: asyncio.Future[Wrapper] = asyncio.get_running_loop().create_future()
        self._pending[seq] = future

        response = self._responses.get(opcode)
        if callable(response) and not hasattr(response, "model_dump"):
            response = response(payload_model)

        if response is None:
            response = EmptyPayload()

        wrapper = Wrapper(opcode=opcode, seq=seq, payload=response)
        future.set_result(wrapper)
        return future


@pytest.fixture
def mock_transport() -> MockTransport:
    return MockTransport(phone=71234567890, token="initial_token")
