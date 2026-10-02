from random import choice, randint
from typing import Final

import ua_generator
from websockets.typing import Origin


DEFAULT_WEB_HEADER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)
WEB_SCREEN = "1080x1920 1.0x"

# user agent
APP_VERSION: Final[str] = "26.17.1"
WEB_VERSION: Final[str] = "26.10.1"
CMD: Final[int] = 0
VER: Final[int] = 11
SYNC_CHAT_COUNT: Final[int] = 40
CHATS_SYNC: Final[int] = -1
CONTACTS_SYNC: Final[int] = -1
PRESENCE_SYNC: Final[int] = -1
DRAFT_SYNC: Final[int] = -1
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
CONNECT_MAX_ATTEMPTS: Final[int] = 3
CONNECT_RETRY_DELAY: Final[float] = 1.0
