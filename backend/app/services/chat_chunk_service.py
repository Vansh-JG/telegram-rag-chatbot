"""Conversation-window chunking for Telegram message history."""

from collections import Counter
from datetime import datetime


WINDOW_SIZE = 10
WINDOW_OVERLAP = 3
WINDOW_STEP = WINDOW_SIZE - WINDOW_OVERLAP


def _format_timestamp(timestamp: str) -> str:
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return timestamp

    return dt.strftime("%Y-%m-%d %H:%M")


def _build_chunk(window: list[dict]) -> dict:
    sender_counter = Counter(message["sender_id"] for message in window if message["sender_id"])
    sender_ids = sorted(sender_counter.keys())
    mentions_user_ids = sorted(
        {
            mentioned_user_id
            for message in window
            for mentioned_user_id in message.get("mentions_user_ids", [])
            if mentioned_user_id
        }
    )
    chunk_lines = [
        f'{message["sender_display_name"]} ({_format_timestamp(message["timestamp"])}): {message["text"]}'
        for message in window
    ]

    return {
        "chunk_text": "\n".join(chunk_lines),
        "chat_id": window[0]["chat_id"],
        "chat_type": window[0]["chat_type"],
        "chat_name": window[0]["chat_name"],
        "sender_ids": sender_ids,
        "primary_speaker_id": sender_counter.most_common(1)[0][0] if sender_counter else "",
        "mentions_user_ids": mentions_user_ids,
        "timestamp_start": window[0]["timestamp"],
        "timestamp_end": window[-1]["timestamp"],
        "source": "telegram",
    }


def chunk_messages(messages: list[dict]) -> list[dict]:
    chunks = []
    messages_by_chat: dict[str, list[dict]] = {}

    for message in messages:
        if not message.get("text"):
            continue
        messages_by_chat.setdefault(message["chat_id"], []).append(message)

    for chat_messages in messages_by_chat.values():
        ordered_messages = sorted(chat_messages, key=lambda item: item["timestamp"])
        if len(ordered_messages) <= WINDOW_SIZE:
            chunks.append(_build_chunk(ordered_messages))
            continue

        start = 0
        while start < len(ordered_messages):
            window = ordered_messages[start : start + WINDOW_SIZE]
            if not window:
                break
            chunks.append(_build_chunk(window))
            if start + WINDOW_SIZE >= len(ordered_messages):
                break
            start += WINDOW_STEP

    return chunks
