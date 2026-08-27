from .schema import UserAgent, WebUserAgent, DeviceType
from .constants import APP_VERSION, DEFAULT_WEB_HEADER_USER_AGENT, WEB_VERSION


def get_socket_user_agent() -> UserAgent:
    return UserAgent(
        device_type=DeviceType.DESKTOP,
        app_version=APP_VERSION,
        locale="ru",
        device_locale="ru",
        os_version="Windows 11",
        device_name="Lenovo",
        screen="1080x2340",
        timezone="Europe/Moscow",
    )

def get_web_user_agent() -> UserAgent:
    return WebUserAgent(
        device_type=DeviceType.WEB,
        header_user_agent=DEFAULT_WEB_HEADER_USER_AGENT,
        app_version=WEB_VERSION,
        locale="ru",
        device_locale="ru",
        os_version="Windows 11",
        device_name="Chrome",
        screen="1080x1920 1.0x",
        timezone="Europe/Moscow"
    )
