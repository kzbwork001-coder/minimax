from typing import Final

from websockets.typing import Origin

# user agent
APP_VERSION: Final[str] = "26.12.0"
USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)
DEVICE_NAME: Final[str] = "Chrome"
DEVICE_LOCALE: Final[str] = "ru"
LOCALE: Final[str] = "ru"
OS_VERSION: Final[str] = "Windows"
SCREEN: Final[str] = "1080x1920 1.0x"
TIMEZONE: Final[str] = "Europe/Moscow"
CMD: Final[int] = 0
VER: Final[int] = 11
SYNC_CHAT_COUNT: Final[int] = 40
CHATS_SYNC: Final[int] = 0
CONTACTS_SYNC: Final[int] = 0
PRESENCE_SYNC: Final[int] = 0
DRAFT_SYNC: Final[int] = 0
SYNC_INTERACTIVE: Final[bool] = True
PING_INTERVAL_SECONDS: Final[int] = 30

# websocket
WEBSOCKET_URI: Final[str] = "wss://ws-api.oneme.ru/websocket"
WEBSOCKET_ORIGIN: Final[Origin] = Origin("https://web.max.ru")

# socket
SOCKET_HOST: Final[str] = "api.oneme.ru"
SOCKET_PORT: Final[int] = 443
RECV_LOOP_BACKOFF_DELAY: Final[float] = 0.5
DEFAULT_TIMEOUT: Final[float] = 20.0
CONNECT_MAX_ATTEMPTS: Final[int] = 3
CONNECT_RETRY_DELAY: Final[float] = 1.0
