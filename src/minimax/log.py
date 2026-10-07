import json
import logging
from typing import Any

from pydantic import BaseModel

LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",  # cyan
    logging.INFO: "\033[32m",  # green
    logging.WARNING: "\033[33m",  # yellow
    logging.ERROR: "\033[31m",  # red
    logging.CRITICAL: "\033[1;31m",  # bold red
}
RESET = "\033[0m"
GRAY = "\033[90m"
BOLD = "\033[1m"


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = LEVEL_COLORS.get(record.levelno, RESET)
        msg = record.getMessage()
        asctime = f"{GRAY}{self.formatTime(record, self.datefmt)}{RESET}"
        levelname = f"{color}{record.levelname:<7}{RESET}"
        name = f"{BOLD}{record.name}{RESET}"
        return f"{asctime} | {levelname} | {name} | {color}{msg}{RESET}"


def setup(level: int = logging.DEBUG) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter(datefmt="%H:%M:%S"))
    logging.basicConfig(level=level, handlers=[handler])
    logging.getLogger("websockets").setLevel(logging.WARNING)


SECRET_KEYS = frozenset({"token", "password"})
REDACTED = "***"


def redact(value: Any) -> Any:
    if isinstance(value, BaseModel):
        value = value.model_dump(by_alias=True)
    if isinstance(value, dict):
        return {
            k: REDACTED if isinstance(k, str) and k.lower() in SECRET_KEYS else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


class Redacted:
    __slots__ = ("_value",)

    def __init__(self, value: Any) -> None:
        self._value = value

    def __str__(self) -> str:
        value = self._value
        if isinstance(value, (str, bytes)):
            try:
                value = json.loads(value)
            except ValueError:
                return f"<{len(self._value)} unparsed chars>"
        return json.dumps(redact(value), ensure_ascii=False, default=str)
