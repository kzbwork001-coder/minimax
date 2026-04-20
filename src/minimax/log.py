import logging

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
