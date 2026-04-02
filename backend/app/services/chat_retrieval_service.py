"""Scoped retrieval for Telegram conversation chunks."""

from datetime import datetime, timezone
import re

from app.db.vector_store import query_telegram_chunks
from app.services.embedding_service import generate_embeddings
from app.services.identity_service import list_users, resolve_name
from app.services.relationship_service import get_allowed_chat_ids


MAX_CANDIDATE_NAME_TOKENS = 3
NAME_STOPWORDS = {
    "a",
    "about",
    "and",
    "did",
    "does",
    "from",
    "in",
    "me",
    "our",
    "said",
    "say",
    "tell",
    "that",
    "the",
    "they",
    "trip",
    "what",
    "who",
    "with",
}


def _extract_candidate_names(query: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9_']+", query)
    candidates: list[str] = []

    for size in range(MAX_CANDIDATE_NAME_TOKENS, 0, -1):
        for start in range(0, len(tokens) - size + 1):
            phrase = " ".join(tokens[start : start + size]).strip()
            if not phrase:
                continue

            normalized_phrase = phrase.lower()
            if normalized_phrase in NAME_STOPWORDS:
                continue

            if size == 1 and normalized_phrase in NAME_STOPWORDS:
                continue

            candidates.append(phrase)

    return candidates


def _detect_person_user_id(query: str) -> str | None:
    for candidate in _extract_candidate_names(query):
        resolved_user_id = resolve_name(candidate)
        if resolved_user_id:
            return resolved_user_id

    normalized_query = query.lower()
    best_match = None
    best_length = 0

    for user in list_users():
        for display_name in user["display_names"]:
            normalized_name = display_name.lower()
            if normalized_name and normalized_name in normalized_query:
                if len(normalized_name) > best_length:
                    best_match = user["user_id"]
                    best_length = len(normalized_name)

    return best_match


def _compute_recency_score(timestamp_end: str) -> float:
    try:
        chunk_time = datetime.fromisoformat(timestamp_end.replace("Z", "+00:00"))
    except ValueError:
        return 0.0

    age_days = (datetime.now(timezone.utc) - chunk_time).days
    if age_days <= 7:
        return 1.0
    if age_days >= 90:
        return 0.0

    remaining_window = 90 - 7
    return max(0.0, 1 - ((age_days - 7) / remaining_window))


def _score_chunk(chunk: dict) -> float:
    distance = float(chunk.get("distance", 1.0))
    semantic_score = 1 / (1 + max(distance, 0.0))
    recency_score = _compute_recency_score(chunk.get("timestamp_end", ""))
    return semantic_score * 0.8 + recency_score * 0.2


async def retrieve_telegram_context(query: str, top_k: int = 5) -> list[dict]:
    embedding = generate_embeddings([query])[0]
    resolved_user_id = _detect_person_user_id(query)
    filters = None

    if resolved_user_id:
        allowed_chat_ids = get_allowed_chat_ids(resolved_user_id)
        scoped_chat_ids = (
            allowed_chat_ids["direct_chat_ids"] + allowed_chat_ids["group_chat_ids"]
        )
        if not scoped_chat_ids:
            return []

        filters = {
            "sender_ids": resolved_user_id,
            "chat_id_in": scoped_chat_ids,
        }

    retrieved_chunks = query_telegram_chunks(
        embedding=embedding,
        filters=filters,
        top_k=max(top_k * 5, top_k),
    )

    for chunk in retrieved_chunks:
        chunk["final_score"] = _score_chunk(chunk)

    ranked_chunks = sorted(
        retrieved_chunks, key=lambda chunk: chunk["final_score"], reverse=True
    )

    return ranked_chunks[:top_k]


async def retrieve_context_for_user_id(user_id: str, query: str, top_k: int = 5) -> list[dict]:
    embedding = generate_embeddings([query])[0]
    allowed_chat_ids = get_allowed_chat_ids(user_id)
    scoped_chat_ids = allowed_chat_ids["direct_chat_ids"] + allowed_chat_ids["group_chat_ids"]

    if not scoped_chat_ids:
        return []

    retrieved_chunks = query_telegram_chunks(
        embedding=embedding,
        filters={"chat_id_in": scoped_chat_ids},
        top_k=max(top_k * 5, top_k),
    )

    for chunk in retrieved_chunks:
        chunk["final_score"] = _score_chunk(chunk)

    ranked_chunks = sorted(
        retrieved_chunks, key=lambda chunk: chunk["final_score"], reverse=True
    )

    return ranked_chunks[:top_k]
