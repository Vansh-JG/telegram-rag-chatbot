"""Telegram ingestion service that exports chats into retrieval-ready chunks."""

from datetime import timezone
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import MessageEntityMentionName, User

from app.core.config import settings
from app.db.vector_store import store_telegram_chunks
from app.services.chat_chunk_service import chunk_messages
from app.services.embedding_service import generate_embeddings
from app.services.identity_service import upsert_user
from app.services.relationship_service import register_chat_participant


STORAGE_DIR = Path(__file__).resolve().parents[3] / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _require_telegram_settings() -> None:
    missing = [
        name
        for name, value in {
            "TELEGRAM_API_ID": settings.telegram_api_id,
            "TELEGRAM_API_HASH": settings.telegram_api_hash,
            "TELEGRAM_PHONE": settings.telegram_phone,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing Telegram configuration: {', '.join(missing)}")


def _build_client() -> TelegramClient:
    session_name = settings.telegram_session_name or "telegram_session"
    session_path = STORAGE_DIR / session_name
    return TelegramClient(
        str(session_path),
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
    )


def _display_name(entity) -> str:
    if entity is None:
        return "Unknown"

    if getattr(entity, "title", None):
        return entity.title

    parts = [getattr(entity, "first_name", None), getattr(entity, "last_name", None)]
    display_name = " ".join(part for part in parts if part)
    if display_name:
        return display_name

    if getattr(entity, "username", None):
        return entity.username

    return str(getattr(entity, "id", "Unknown"))


async def _get_participants(client: TelegramClient, dialog, me_id: str) -> list[str]:
    entity = dialog.entity
    if dialog.is_user:
        return sorted({me_id, str(entity.id)})

    participant_ids = set()
    async for participant in client.iter_participants(entity):
        participant_ids.add(str(participant.id))

    return sorted(participant_ids)


def _extract_mentions(message) -> list[str]:
    mentions = set()
    for entity in message.entities or []:
        if isinstance(entity, MessageEntityMentionName) and entity.user_id:
            mentions.add(str(entity.user_id))
    return sorted(mentions)


async def _register_dialog_participants(
    client: TelegramClient,
    dialog,
    me_id: str,
) -> None:
    chat_id = str(dialog.id)
    chat_type = "direct" if dialog.is_user else "group"

    if dialog.is_user:
        user = dialog.entity
        if str(user.id) != me_id:
            upsert_user(str(user.id), _display_name(user), chat_id)
            register_chat_participant(str(user.id), chat_id, chat_type)
        return

    entity = dialog.entity
    async for participant in client.iter_participants(entity):
        user_id = str(participant.id)
        if user_id == me_id:
            continue
        upsert_user(user_id, _display_name(participant), chat_id)
        register_chat_participant(user_id, chat_id, chat_type)


async def _export_dialog_messages(
    client: TelegramClient,
    dialog,
    me_id: str,
) -> list[dict]:
    if not (dialog.is_user or dialog.is_group or getattr(dialog.entity, "megagroup", False)):
        return []

    chat_id = str(dialog.id)
    chat_type = "direct" if dialog.is_user else "group"
    chat_name = dialog.name or _display_name(dialog.entity)
    participants = await _get_participants(client, dialog, me_id)
    await _register_dialog_participants(client, dialog, me_id)

    sender_cache: dict[str, str] = {}
    exported_messages = []

    async for message in client.iter_messages(dialog.entity, reverse=True):
        text = (message.message or "").strip()
        if not text:
            continue

        sender_id = str(message.sender_id) if message.sender_id is not None else ""
        if sender_id not in sender_cache:
            sender = await message.get_sender()
            sender_cache[sender_id] = _display_name(sender)
            if isinstance(sender, User) and sender_id and sender_id != me_id:
                upsert_user(sender_id, sender_cache[sender_id], chat_id)
                register_chat_participant(sender_id, chat_id, chat_type)

        exported_messages.append(
            {
                "message_id": f"{chat_id}:{message.id}",
                "chat_id": chat_id,
                "chat_name": chat_name,
                "chat_type": chat_type,
                "sender_id": sender_id,
                "sender_display_name": sender_cache.get(sender_id, "Unknown"),
                "text": text,
                "timestamp": message.date.astimezone(timezone.utc).isoformat(),
                "participants": participants,
                "mentions_user_ids": _extract_mentions(message),
            }
        )

    return exported_messages


async def ingest_all_chats() -> dict:
    _require_telegram_settings()

    client = _build_client()
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        raise RuntimeError(
            "Telegram session is not authorized. Create the session file in storage/ before ingesting chats."
        )

    try:
        me = await client.get_me()
        me_id = str(me.id)
        exported_messages = []
        chat_count = 0

        async for dialog in client.iter_dialogs():
            messages = await _export_dialog_messages(client, dialog, me_id)
            if not messages:
                continue
            chat_count += 1
            exported_messages.extend(messages)

        chunks = chunk_messages(exported_messages)
        embeddings = generate_embeddings([chunk["chunk_text"] for chunk in chunks]) if chunks else []

        prepared_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            prepared_chunk = dict(chunk)
            prepared_chunk["embedding"] = embedding
            prepared_chunks.append(prepared_chunk)

        stored_count = store_telegram_chunks(prepared_chunks)

        return {
            "chats": chat_count,
            "messages": len(exported_messages),
            "chunks": stored_count,
        }
    finally:
        await client.disconnect()
