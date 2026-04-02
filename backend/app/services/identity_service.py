"""Identity index for Telegram users backed by SQLite."""

import json
import sqlite3
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[3] / "storage" / "identity.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_names TEXT NOT NULL,
            chat_ids TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    return conn


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _load_json_array(value: str) -> list[str]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []

    return [item for item in data if isinstance(item, str) and item.strip()]


def upsert_user(user_id: str, display_name: str, chat_id: str) -> None:
    normalized_display_name = display_name.strip()
    normalized_chat_id = chat_id.strip()
    if not user_id or not normalized_display_name or not normalized_chat_id:
        return

    with _get_connection() as conn:
        row = conn.execute(
            "SELECT display_names, chat_ids FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        display_names = set()
        chat_ids = set()

        if row:
            display_names.update(_load_json_array(row["display_names"]))
            chat_ids.update(_load_json_array(row["chat_ids"]))

        display_names.add(normalized_display_name)
        chat_ids.add(normalized_chat_id)

        conn.execute(
            """
            INSERT INTO users (user_id, display_names, chat_ids, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                display_names = excluded.display_names,
                chat_ids = excluded.chat_ids,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                json.dumps(sorted(display_names)),
                json.dumps(sorted(chat_ids)),
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_user(user_id: str) -> dict | None:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, display_names, chat_ids, updated_at FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "user_id": row["user_id"],
        "display_names": _load_json_array(row["display_names"]),
        "chat_ids": _load_json_array(row["chat_ids"]),
        "updated_at": row["updated_at"],
    }


def list_users() -> list[dict]:
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT user_id, display_names, chat_ids, updated_at FROM users ORDER BY updated_at DESC"
        ).fetchall()

    users = []
    for row in rows:
        chat_ids = _load_json_array(row["chat_ids"])
        users.append(
            {
                "user_id": row["user_id"],
                "display_names": _load_json_array(row["display_names"]),
                "chat_ids": chat_ids,
                "chat_count": len(chat_ids),
                "updated_at": row["updated_at"],
            }
        )

    return users


def resolve_name(name: str) -> str | None:
    normalized_query = _normalize_name(name)
    if not normalized_query:
        return None

    users = list_users()
    best_user_id = None
    best_score = 0.0

    for user in users:
        for display_name in user["display_names"]:
            normalized_display_name = _normalize_name(display_name)
            if not normalized_display_name:
                continue

            if normalized_query == normalized_display_name:
                return user["user_id"]

            if normalized_query in normalized_display_name or normalized_display_name in normalized_query:
                score = 0.95
            else:
                query_tokens = set(normalized_query.split())
                name_tokens = set(normalized_display_name.split())
                overlap = len(query_tokens & name_tokens)
                if overlap:
                    score = 0.75 + (overlap / max(len(name_tokens), 1)) * 0.2
                else:
                    score = SequenceMatcher(
                        None, normalized_query, normalized_display_name
                    ).ratio()

            if score > best_score:
                best_score = score
                best_user_id = user["user_id"]

    if best_score >= 0.7:
        return best_user_id

    return None
