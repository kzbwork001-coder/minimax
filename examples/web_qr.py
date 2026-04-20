"""WebClient — login via QR code scan."""

import asyncio
import logging
import sys

from dump import dump_account
from minimax import WebClient, log

log.setup()
logger = logging.getLogger("examples")


async def main() -> None:
    phone = sys.argv[1]

    async with WebClient(phone) as client:
        await client.login_by_qr(
            qr_callback=lambda link: logger.info("Scan QR code: %s", link),
        )
        await dump_account(client)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <phone>")
        sys.exit(1)
    asyncio.run(main())
