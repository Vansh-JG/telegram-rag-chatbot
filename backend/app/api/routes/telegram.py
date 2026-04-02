"""Telegram ingestion and chat endpoints."""

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.chat_retrieval_service import retrieve_telegram_context
from app.services.identity_service import list_users
from app.services.telegram_service import ingest_all_chats


router = APIRouter()
client = OpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a personal assistant with access to the user's Telegram conversations.
Answer questions using ONLY the provided message context.
If the context is insufficient, say so - do not infer or hallucinate.
Prefer direct messages over group chats when both are available.
Always attribute statements to the correct person."""


class TelegramChatRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class TelegramDraftRequest(BaseModel):
    user_id: str
    draft: str
    top_k: int = Field(default=6, ge=1, le=20)


class TelegramSendRequest(BaseModel):
    user_id: str
    message: str


@router.post("/ingest")
async def ingest_telegram_chats() -> dict:
    try:
        stats = await ingest_all_chats()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "stats": stats}


@router.get("/contacts")
def get_telegram_contacts() -> list[dict]:
    users = list_users()
    return [
        {
            "user_id": user["user_id"],
            "display_names": user["display_names"],
            "chat_count": user["chat_count"],
        }
        for user in users
    ]


@router.post("/chat")
async def telegram_chat(request: TelegramChatRequest) -> dict:
    try:
        sources = await retrieve_telegram_context(request.query, request.top_k)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not sources:
        return {
            "answer": "I don't have enough Telegram context to answer that.",
            "sources": [],
        }

    ordered_sources = sorted(
        sources,
        key=lambda source: (0 if source["chat_type"] == "direct" else 1, -source["final_score"]),
    )
    context_blocks = []
    for source in ordered_sources:
        chat_label = (
            f'[Direct Chat with {source["chat_name"]}]'
            if source["chat_type"] == "direct"
            else f'[Group: {source["chat_name"]}]'
        )
        context_blocks.append(f'{chat_label}\n{source["chunk_text"]}')

    user_prompt = "\n\n".join(context_blocks) + f"\n\nQuestion: {request.query}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": ordered_sources,
    }


@router.post("/draft")
async def draft_telegram_message(request: TelegramDraftRequest) -> dict:
    from app.services.telegram_send_service import generate_message_draft

    try:
        return await generate_message_draft(
            user_id=request.user_id,
            draft=request.draft,
            top_k=request.top_k,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/send")
async def send_telegram_message(request: TelegramSendRequest) -> dict:
    from app.services.telegram_send_service import send_message_to_user

    try:
        return await send_message_to_user(
            user_id=request.user_id,
            message=request.message,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
