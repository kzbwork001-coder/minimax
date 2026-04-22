import logging
from datetime import datetime

from minimax import Chat, ChatType, Contact, Message
from minimax.schema.models import Audio, File, Photo, Sticker, Video

logger = logging.getLogger("examples")


def format_attachment(attach) -> str:
    if isinstance(attach, Photo):
        return f"[Photo {attach.photo_id} {attach.base_url}]"
    elif isinstance(attach, Video):
        return f"[Video {attach.video_id} {attach.width}x{attach.height}]"
    elif isinstance(attach, Audio):
        return f"[Audio {attach.audio_id} {attach.duration}s]"
    elif isinstance(attach, File):
        return f"[File {attach.file_id} {attach.name}]"
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


def dump_messages(messages: list[Message]) -> None:
    logger.info("=== Messages (%d) ===", len(messages))
    for msg in messages:
        ts = datetime.fromtimestamp(msg.time / 1000).strftime("%Y-%m-%d %H:%M")
        text = msg.text or ""
        parts = [f"  [{ts}] sender={msg.sender}: {text}"]

        for attach in msg.attaches:
            parts.append(f"    {format_attachment(attach)}")

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
            messages = await client.fetch_messages(chat.id, history_from, history_to)
            dump_messages(messages)
