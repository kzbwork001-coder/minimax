import logging
from typing import TYPE_CHECKING

from .schema import ApiError, Event

if TYPE_CHECKING:
    from .client.client import Client

log = logging.getLogger(__name__)


def on_error(error) -> None:
    if isinstance(error, ApiError):
        res = error.error_res
        log.error("Error: %s — %s - %s", res.error, res.title, res.message)
    else:
        log.error("Error: %s", error)


def register_default_listeners(client: "Client") -> None:
    client.events.on(Event.BACKGROUND_TASK_ERROR, on_error)
    client.events.on(Event.SUCCESSFUL_LOGIN, lambda token: client.sync(token))
