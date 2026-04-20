"""WebClient — authenticate with a pre-existing token."""

import asyncio
import sys

from dump import dump_account
from minimax import WebClient, log

log.setup()


async def main() -> None:
    phone = sys.argv[1]
    token = sys.argv[2]

    async with WebClient(phone) as client:
        await client.sync(token)
        await dump_account(client)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <phone> <token>")
        sys.exit(1)
    asyncio.run(main())
