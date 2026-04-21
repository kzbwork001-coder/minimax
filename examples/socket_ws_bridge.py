import asyncio
import json
import logging

from websockets.asyncio.server import ServerConnection, serve

from dump import dump_account
from minimax import SocketClient, log

log.setup()
logger = logging.getLogger("examples.bridge")


async def handle_fe(ws: ServerConnection) -> None:
    phone_msg = json.loads(await ws.recv())
    assert phone_msg["type"] == "phone"

    pending_code: asyncio.Future[str] | None = None
    pending_password: asyncio.Future[str] | None = None

    async def pump_fe_inputs() -> None:
        nonlocal pending_code, pending_password
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "code" and pending_code and not pending_code.done():
                pending_code.set_result(msg["code"])
            elif msg["type"] == "password" and pending_password and not pending_password.done():
                pending_password.set_result(msg["password"])

    pump_task = asyncio.create_task(pump_fe_inputs())

    async def code_callback() -> str:
        nonlocal pending_code
        pending_code = asyncio.get_running_loop().create_future()
        await ws.send(json.dumps({"type": "code_required"}))
        return await pending_code

    async def password_callback(hint: str) -> str:
        nonlocal pending_password
        pending_password = asyncio.get_running_loop().create_future()
        await ws.send(json.dumps({"type": "password_required", "hint": hint}))
        return await pending_password

    try:
        async with SocketClient(phone_msg["phone"]) as client:
            await client.login_by_phone(code_callback, password_callback)
            await ws.send(json.dumps({"type": "success"}))
            await dump_account(client)
    except Exception as e:
        logger.exception("login failed")
        await ws.send(json.dumps({"type": "error", "message": str(e)}))
    finally:
        pump_task.cancel()


async def main() -> None:
    async with serve(handle_fe, "localhost", 8765):
        logger.info("BE ws server listening on ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
