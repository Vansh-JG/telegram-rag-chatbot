"""Telegram draft generation and outbound send helpers."""

from telethon import TelegramClient

from app.core.config import settings
from app.services.chat_retrieval_service import retrieve_context_for_user_id
from app.services.identity_service import get_user
from app.services.telegram_service import _build_client, _require_telegram_settings
from openai import OpenAI


client = OpenAI(api_key=settings.openai_api_key)

DRAFT_SYSTEM_PROMPT = """You help the user send thoughtful Telegram messages.
Rewrite the user's draft into a polished message addressed to the selected recipient.
Use the provided Telegram conversation context only to match tone, names, and relevant facts.
Do not invent facts, plans, or commitments not present in the user's draft or context.
Keep the meaning and intent of the user's draft intact.
Return only the final message text with no preamble or explanation."""


def _require_user(user_id: str) -> dict:
    user = get_user(user_id)
    if user is None:
        raise RuntimeError("Selected Telegram contact was not found in the local index.")
    return user


async def generate_message_draft(user_id: str, draft: str, top_k: int = 6) -> dict:
    _require_user(user_id)
    cleaned_draft = draft.strip()
    if not cleaned_draft:
        raise RuntimeError("Draft message cannot be empty.")

    sources = await retrieve_context_for_user_id(user_id=user_id, query=cleaned_draft, top_k=top_k)

    context_blocks = []
    for source in sources:
        chat_label = (
            f'[Direct Chat with {source["chat_name"]}]'
            if source["chat_type"] == "direct"
            else f'[Group: {source["chat_name"]}]'
        )
        context_blocks.append(f'{chat_label}\n{source["chunk_text"]}')

    user_prompt = "\n\n".join(
        [
            f"Recipient user id: {user_id}",
            f"Original draft:\n{cleaned_draft}",
            "Conversation context:",
            "\n\n".join(context_blocks) if context_blocks else "No relevant Telegram context found.",
        ]
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": DRAFT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    refined_message = (response.choices[0].message.content or "").strip()
    if not refined_message:
        raise RuntimeError("Could not generate a refined draft.")

    return {
        "refined_message": refined_message,
        "sources": sources,
    }


async def send_message_to_user(user_id: str, message: str) -> dict:
    _require_telegram_settings()
    user = _require_user(user_id)

    cleaned_message = message.strip()
    if not cleaned_message:
        raise RuntimeError("Message cannot be empty.")

    telegram_client: TelegramClient = _build_client()
    await telegram_client.connect()
    if not await telegram_client.is_user_authorized():
        await telegram_client.disconnect()
        raise RuntimeError(
            "Telegram session is not authorized. Create the session file in storage/ before sending messages."
        )

    try:
        entity = await telegram_client.get_input_entity(int(user_id))
        sent_message = await telegram_client.send_message(entity, cleaned_message)
        return {
            "status": "sent",
            "recipient_user_id": user_id,
            "recipient_name": user["display_names"][0] if user["display_names"] else user_id,
            "message_id": sent_message.id,
        }
    finally:
        await telegram_client.disconnect()
