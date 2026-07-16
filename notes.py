"""
Research Notes
----------------
Simple CRUD layer so users (or the agent itself, via the save_note tool)
can persist key findings per research session.
"""
import datetime
from memory import get_db


def add_note(session_id: str, title: str, content: str) -> dict:
    created_at = datetime.datetime.utcnow().isoformat()
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO notes (session_id, title, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, title, content, created_at),
        )
        note_id = cur.lastrowid
    return {"id": note_id, "title": title, "content": content, "created_at": created_at}


def list_notes(session_id: str) -> list:
    with get_db() as db:
        rows = db.execute(
            "SELECT id, title, content, created_at FROM notes WHERE session_id = ? ORDER BY id DESC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_note(session_id: str, note_id: int) -> bool:
    with get_db() as db:
        cur = db.execute(
            "DELETE FROM notes WHERE session_id = ? AND id = ?", (session_id, note_id)
        )
        return cur.rowcount > 0
