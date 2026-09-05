"""
Persistent conversation storage using SQLite (Python stdlib — no extra install).

Schema:
  conversations  — one row per chat session
  messages       — one row per message, linked to a conversation

All timestamps are stored as ISO-8601 strings (UTC).
Sources (list of dicts) are stored as JSON strings and parsed back on read.
"""

import sqlite3
import json
import uuid
import os
from datetime import datetime, timezone
from app.config import DB_PATH


def _get_conn() -> sqlite3.Connection:
    """Open a connection to the SQLite database. Called per operation."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # allows dict-style access: row["column"]
    return conn


def init_db():
    """
    Create the data/ directory and tables if they don't already exist.
    Safe to call multiple times (uses IF NOT EXISTS).
    Called at app startup from main.py and 01_chat.py.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role            TEXT NOT NULL,
                content         TEXT NOT NULL,
                model_id        TEXT    DEFAULT '',
                model_name      TEXT    DEFAULT '',
                input_tokens    INTEGER DEFAULT 0,
                output_tokens   INTEGER DEFAULT 0,
                cost_usd        REAL    DEFAULT 0.0,
                routing_reason  TEXT    DEFAULT '',
                has_image       INTEGER DEFAULT 0,
                sources         TEXT    DEFAULT '[]',
                created_at      TEXT    NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id);
        """)
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ── Conversations ──────────────────────────────────────────────────────────────

def create_conversation(title: str) -> str:
    """
    Insert a new conversation row.
    Returns the new conversation ID (UUID string).
    """
    conv_id = str(uuid.uuid4())
    now     = _now()
    conn    = _get_conn()
    try:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?,?,?,?)",
            (conv_id, title[:120], now, now)
        )
        conn.commit()
    finally:
        conn.close()
    return conv_id


def get_all_conversations() -> list[dict]:
    """
    Return all conversations ordered by most-recently-updated first.
    Each dict includes a message_count field.
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) AS message_count
            FROM   conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            GROUP  BY c.id
            ORDER  BY c.updated_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM messages     WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?",             (conversation_id,))
        conn.commit()
    finally:
        conn.close()


# ── Messages ───────────────────────────────────────────────────────────────────

def save_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    model_id:       str   = "",
    model_name:     str   = "",
    input_tokens:   int   = 0,
    output_tokens:  int   = 0,
    cost_usd:       float = 0.0,
    routing_reason: str   = "",
    has_image:      int   = 0,
    sources:        list  = None,
) -> str:
    """
    Insert one message row. Returns the new message ID.
    Also updates the conversation's updated_at timestamp.
    """
    msg_id      = str(uuid.uuid4())
    now         = _now()
    sources_str = json.dumps(sources or [])

    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO messages
                (id, conversation_id, role, content, model_id, model_name,
                 input_tokens, output_tokens, cost_usd, routing_reason,
                 has_image, sources, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            msg_id, conversation_id, role, content,
            model_id, model_name, input_tokens, output_tokens,
            cost_usd, routing_reason, has_image, sources_str, now
        ))
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id)
        )
        conn.commit()
    finally:
        conn.close()
    return msg_id


def get_conversation_messages(conversation_id: str) -> list[dict]:
    """
    Return all messages for a conversation ordered by created_at ASC.
    Parses the sources JSON string back into a Python list.
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT * FROM messages
            WHERE  conversation_id = ?
            ORDER  BY created_at ASC
        """, (conversation_id,)).fetchall()

        result = []
        for r in rows:
            msg = dict(r)
            # Parse sources back from JSON string
            try:
                msg["sources"] = json.loads(msg.get("sources") or "[]")
            except (json.JSONDecodeError, TypeError):
                msg["sources"] = []
            result.append(msg)
        return result
    finally:
        conn.close()


def get_conversation_stats(conversation_id: str) -> dict:
    """
    Return aggregate stats for a single conversation.
    Used on the analytics page conversation detail view.
    """
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT
                COUNT(*)              AS total_messages,
                SUM(input_tokens)     AS total_input_tokens,
                SUM(output_tokens)    AS total_output_tokens,
                SUM(cost_usd)         AS total_cost_usd
            FROM messages
            WHERE conversation_id = ?
        """, (conversation_id,)).fetchone()

        models = conn.execute("""
            SELECT DISTINCT model_name
            FROM   messages
            WHERE  conversation_id = ? AND model_name != ''
        """, (conversation_id,)).fetchall()

        return {
            "total_messages":      row["total_messages"]      or 0,
            "total_input_tokens":  row["total_input_tokens"]  or 0,
            "total_output_tokens": row["total_output_tokens"] or 0,
            "total_cost_usd":      row["total_cost_usd"]      or 0.0,
            "models_used":         [m["model_name"] for m in models],
        }
    finally:
        conn.close()


# ── Aggregate stats (for analytics dashboard) ──────────────────────────────────

def get_all_stats() -> dict:
    """
    Return aggregate statistics across ALL conversations.
    Used by app/pages/02_analytics.py and app/main.py.

    Returns:
        {
          total_conversations: int,
          total_messages:      int,
          total_input_tokens:  int,
          total_output_tokens: int,
          total_cost_usd:      float,
          messages_by_model:   {model_name: count},
          daily_costs:         [{date: str, cost_usd: float, message_count: int}]
        }
    """
    conn = _get_conn()
    try:
        # Overall totals
        totals = conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM conversations)       AS total_conversations,
                COUNT(*)                                   AS total_messages,
                COALESCE(SUM(input_tokens),  0)            AS total_input_tokens,
                COALESCE(SUM(output_tokens), 0)            AS total_output_tokens,
                COALESCE(SUM(cost_usd),      0.0)          AS total_cost_usd
            FROM messages
        """).fetchone()

        # Per-model message counts
        model_rows = conn.execute("""
            SELECT model_name, COUNT(*) AS cnt
            FROM   messages
            WHERE  model_name != ''
            GROUP  BY model_name
            ORDER  BY cnt DESC
        """).fetchall()
        messages_by_model = {r["model_name"]: r["cnt"] for r in model_rows}

        # Daily cost trend — group by date portion of created_at
        daily_rows = conn.execute("""
            SELECT
                SUBSTR(created_at, 1, 10)   AS date,
                COALESCE(SUM(cost_usd), 0.0) AS cost_usd,
                COUNT(*)                     AS message_count
            FROM   messages
            GROUP  BY SUBSTR(created_at, 1, 10)
            ORDER  BY date ASC
        """).fetchall()
        daily_costs = [dict(r) for r in daily_rows]

        return {
            "total_conversations": totals["total_conversations"] or 0,
            "total_messages":      totals["total_messages"]      or 0,
            "total_input_tokens":  totals["total_input_tokens"]  or 0,
            "total_output_tokens": totals["total_output_tokens"] or 0,
            "total_cost_usd":      totals["total_cost_usd"]      or 0.0,
            "messages_by_model":   messages_by_model,
            "daily_costs":         daily_costs,
        }
    finally:
        conn.close()


def get_all_messages_flat(limit: int = 100) -> list[dict]:
    """
    Return the most recent `limit` assistant messages across all conversations.
    Used by the analytics page to build per-message cost/token charts.
    """
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT m.*, c.title AS conversation_title
            FROM   messages m
            JOIN   conversations c ON c.id = m.conversation_id
            WHERE  m.role = 'assistant'
            ORDER  BY m.created_at DESC
            LIMIT  ?
        """, (limit,)).fetchall()

        result = []
        for r in rows:
            msg = dict(r)
            try:
                msg["sources"] = json.loads(msg.get("sources") or "[]")
            except (json.JSONDecodeError, TypeError):
                msg["sources"] = []
            result.append(msg)
        return result
    finally:
        conn.close()
