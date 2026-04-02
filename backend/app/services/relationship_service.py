"""Relationship index for mapping Telegram users to shared chats."""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[3] / "storage" / "relationships.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS relationships (
            user_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            chat_type TEXT NOT NULL,
            PRIMARY KEY (user_id, chat_id)
        )
        """
    )
    return conn


def register_chat_participant(user_id: str, chat_id: str, chat_type: str) -> None:
    if not user_id or not chat_id or chat_type not in {"direct", "group"}:
        return

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO relationships (user_id, chat_id, chat_type)
            VALUES (?, ?, ?)
            """,
            (user_id, chat_id, chat_type),
        )


def get_allowed_chat_ids(user_id: str) -> dict:
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT chat_id, chat_type FROM relationships WHERE user_id = ?",
            (user_id,),
        ).fetchall()

    direct_chat_ids = [row["chat_id"] for row in rows if row["chat_type"] == "direct"]
    group_chat_ids = [row["chat_id"] for row in rows if row["chat_type"] == "group"]

    return {
        "direct_chat_ids": direct_chat_ids,
        "group_chat_ids": group_chat_ids,
    }


def get_mutual_groups(user_id: str) -> list[str]:
    return get_allowed_chat_ids(user_id)["group_chat_ids"]
