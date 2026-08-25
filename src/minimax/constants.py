from random import choice, randint
from typing import Final

import ua_generator
from websockets.typing import Origin

# user agent
APP_VERSION: Final[str] = "26.17.1"
WEB_VERSION: Final[str] = "26.8.4"
CMD: Final[int] = 0
VER: Final[int] = 11
SYNC_CHAT_COUNT: Final[int] = 40
CHATS_SYNC: Final[int] = 0
CONTACTS_SYNC: Final[int] = 0
PRESENCE_SYNC: Final[int] = 0
DRAFT_SYNC: Final[int] = 0
SYNC_INTERACTIVE: Final[bool] = True
PING_INTERVAL_SECONDS: Final[int] = 30
REQUEST_TIMEOUT_SECONDS: Final[float] = 60.0

# websocket
WEBSOCKET_URI: Final[str] = "wss://ws-api.oneme.ru/websocket"
WEBSOCKET_ORIGIN: Final[Origin] = Origin("https://web.max.ru")
WEBSOCKET_OPEN_TIMEOUT_SECONDS: Final[float] = 30.0

# socket
SOCKET_HOST: Final[str] = "api2.oneme.ru"
SOCKET_PORT: Final[int] = 443
RECV_LOOP_BACKOFF_DELAY: Final[float] = 0.5
DEFAULT_TIMEOUT: Final[float] = 20.0
CONNECT_MAX_ATTEMPTS: Final[int] = 3
CONNECT_RETRY_DELAY: Final[float] = 1.0

# user agent
DEVICE_NAMES: Final[list[str]] = [
    "Chrome",
    "Firefox",
    "Edge",
    "Safari",
    "Opera",
    "Brave",
    # os
    "Windows 10",
    "Windows 11",
    "macOS Big Sur",
    "macOS Monterey",
    "Ubuntu 22.04",
    "Fedora 36",
    "Debian 11",
]
SCREEN_SIZES: Final[list[str]] = [
    "1920x1080 1.0x",
    "1366x768 1.0x",
    "1440x900 1.0x",
    "1536x864 1.0x",
    "1280x720 1.0x",
    "1600x900 1.0x",
    "1680x1050 1.0x",
    "2560x1440 1.0x",
    "3840x2160 1.0x",
]
OS_VERSIONS: Final[list[str]] = [
    "Windows 10",
    "Windows 11",
    "macOS Big Sur",
    "macOS Monterey",
    "Ubuntu 22.04",
    "Fedora 36",
    "Debian 11",
]
TIMEZONES: Final[list[str]] = [
    "Europe/Moscow",
    "Europe/Kaliningrad",
    "Asia/Yekaterinburg",
    "Asia/Omsk",
    "Asia/Krasnoyarsk",
    "Asia/Yakutsk",
    "Asia/Vladivostok",
]
