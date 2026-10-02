import logging
from datetime import datetime

from minimax import Chat, ChatType, Contact, Message
from minimax.schema.models import Audio, File, Photo, Sticker, Video
import ssl

import aiohttp
import asyncio
import certifi

logger = logging.getLogger("examples")


def format_attachment(attach, video_url: str | None = None, file_url: str | None = None) -> str:
    if isinstance(attach, Photo):
        return f"[Photo {attach.photo_id} {attach.base_url}]"
    elif isinstance(attach, Video):
        return f"[Video {attach.video_id} {attach.width}x{attach.height} {video_url or ''}]"
    elif isinstance(attach, Audio):
        return f"[Audio {attach.audio_id} {attach.duration}s]"
    elif isinstance(attach, File):
        return f"[File {attach.file_id} {attach.name} {file_url or ''}]"
    elif isinstance(attach, Sticker):
        return f"[Sticker {attach.sticker_id}]"
    return f"[{attach.type}]"


def dump_contacts(contacts: list[Contact]) -> None:
    logger.info("=== Contacts (%d) ===", len(contacts))
    for contact in contacts:
        name = contact.names[0].name if contact.names else "Unknown"
        logger.info("  [%d] %s", contact.id, name)


def dump_chats(chats: list[Chat]) -> None:
    logger.info("=== Chats (%d) ===", len(chats))
    for chat in chats:
        last = chat.last_message
        if last and last.text:
            preview = (last.text[:50] + "...") if len(last.text) > 50 else last.text
        else:
            preview = ""
        logger.info("  [%d] %s | last: %s", chat.id, chat.type.value, preview)


async def dump_messages(client, chat_id: int, messages: list[Message]) -> None:
    logger.info("=== Messages (%d) ===", len(messages))
    for msg in messages:
        ts = datetime.fromtimestamp(msg.time / 1000).strftime("%Y-%m-%d %H:%M")
        text = msg.text or ""
        parts = [f"  [{ts}] sender={msg.sender}: {text}"]

        for attach in msg.attaches:
            video_url: str | None = None
            file_url: str | None = None
            user_agent = getattr(client.user_agent, "header_user_agent", None)
            if isinstance(attach, Video) and attach.token:
                video_url = await client.get_video_url(
                    attach.video_id, attach.token
                )
                await download_file_from_url(video_url,user_agent)
            elif isinstance(attach, File):
                file_url = await client.get_file_url(attach.file_id, chat_id, msg.id)
                await download_file_from_url(file_url,user_agent)
            parts.append(f"    {format_attachment(attach, video_url, file_url)}")

        if msg.link:
            parts.append(f"    -> linked: {msg.link.message.id}")

        logger.info("\n".join(parts))


async def dump_account(client) -> None:
    dump_contacts(client.contacts)
    dump_chats(client.chats)

    history_from = datetime(2026, 3, 1)
    history_to = datetime.now()

    for chat in client.chats:
        if chat.type in (ChatType.DIALOG, ChatType.CHANNEL):
            logger.info("--- Fetching messages for chat %d ---", chat.id)
            limit = 10 if chat.type == ChatType.CHANNEL else None
            messages = await client.fetch_messages(chat.id, history_from, history_to, limit=limit)
            await dump_messages(client, chat.id, messages)


_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
async def download_file_from_url(url: str, user_agent: str, max_retries: int = 3, timeout_seconds: int = 30):
    logger.debug(f"Downloading file from URL: {url}")
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    headers = {"User-Agent": user_agent} if user_agent else {}
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, ssl=_SSL_CONTEXT) as resp:
                    if resp.status == 200:
                        file_data: bytes = await resp.read()
                        logger.debug(
                            f"Successfully downloaded file from {url} (attempt {attempt + 1}/{max_retries})"
                        )
                        return file_data
                    else:
                        raise Exception(
                            f"Failed to download file, status code: {resp.status}"
                        )

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(
                f"Connection error downloading file from {url} (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
            else:
                logger.error(
                    f"Failed to download file from {url} after {max_retries} attempts"
                )
                raise e
