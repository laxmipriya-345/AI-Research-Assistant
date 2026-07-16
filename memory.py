"""
Conversation Memory
--------------------
Stores per-session chat history in SQLite and auto-summarizes older
messages once a session grows long, so the agent keeps useful context
without blowing up the token budget on every call.
"""
import sqlite3
import uuid
import datetime
from contextlib import contextmanager

from config import DB_PATH, MEMORY_SUMMARY_TRIGGER


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                summary TEXT DEFAULT '',
                created_at TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                title TEXT,
                content TEXT,
                created_at TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                filename TEXT,
                chunk_index INTEGER,
                content TEXT
            )
        """)


def create_session(title: str) -> dict:
    session_id = str(uuid.uuid4())
    created_at = datetime.datetime.utcnow().isoformat()
    with get_db() as db:
        db.execute(
            "INSERT INTO sessions (id, title, summary, created_at) VALUES (?, ?, '', ?)",
            (session_id, title, created_at),
        )
    return {"id": session_id, "title": title, "created_at": created_at}


def list_sessions() -> list:
    with get_db() as db:
        rows = db.execute("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_session(session_id: str) -> dict:
    with get_db() as db:
        row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None


def add_message(session_id: str, role: str, content: str):
    created_at = datetime.datetime.utcnow().isoformat()
    with get_db() as db:
        db.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, created_at),
        )


def get_messages(session_id: str) -> list:
    with get_db() as db:
        rows = db.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_recent_messages_for_prompt(session_id: str, limit: int = 12) -> list:
    """Return the most recent messages formatted for the Anthropic Messages API."""
    with get_db() as db:
        rows = db.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    rows = list(reversed(rows))
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def maybe_summarize(session_id: str, summarizer_fn):
    """
    If the session has grown past MEMORY_SUMMARY_TRIGGER messages, compress the
    oldest half into a running summary (via summarizer_fn) and delete them,
    keeping the token footprint of long research sessions manageable.
    """
    with get_db() as db:
        count = db.execute(
            "SELECT COUNT(*) as c FROM messages WHERE session_id = ?", (session_id,)
        ).fetchone()["c"]

    if count < MEMORY_SUMMARY_TRIGGER:
        return

    with get_db() as db:
        rows = db.execute(
            "SELECT id, role, content FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, count // 2),
        ).fetchall()
        session = db.execute("SELECT summary FROM sessions WHERE id = ?", (session_id,)).fetchone()

    old_text = "\n".join(f"{r['role']}: {r['content']}" for r in rows)
    new_summary = summarizer_fn(session["summary"], old_text)

    with get_db() as db:
        db.execute("UPDATE sessions SET summary = ? WHERE id = ?", (new_summary, session_id))
        ids = [r["id"] for r in rows]
        db.executemany("DELETE FROM messages WHERE id = ?", [(i,) for i in ids])


def get_summary(session_id: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT summary FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row["summary"] if row else ""
