import asyncio
import contextlib
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from .schema import Event


class EventEmitter:
    def __init__(self):
        self._listeners: dict[Event, list[Callable[..., Any]]] = defaultdict(list)

    def on(self, event: Event, listener: Callable[..., Any]) -> None:
        self._listeners[event].append(listener)

    def off(self, event: Event, listener: Callable[..., Any] | None = None) -> None:
        if listener is None:
            self._listeners[event].clear()
        else:
            with contextlib.suppress(ValueError):
                self._listeners[event].remove(listener)

    def emit(self, event: Event, *args: Any) -> None:
        for listener in self._listeners[event]:
            result = listener(*args)
            if asyncio.iscoroutine(result):
                task = asyncio.create_task(result)
                task.add_done_callback(self.on_task_done)

    def on_task_done(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            self.emit(Event.BACKGROUND_TASK_ERROR, exc)
