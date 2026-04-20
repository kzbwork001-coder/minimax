"""SocketClient — login via phone number + SMS code (+ optional 2FA)."""

import asyncio
import sys

from dump import dump_account
from minimax import SocketClient, log

log.setup()


async def main() -> None:
    phone = sys.argv[1]

    async with SocketClient(phone) as client:
        await client.login_by_phone(
            code_callback=lambda: input("Enter SMS code: "),
            password_callback=lambda hint: input(f"Enter 2FA password (hint: {hint}): "),
        )
        await dump_account(client)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <phone>")
        sys.exit(1)
    asyncio.run(main())
