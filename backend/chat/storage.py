# -*- coding: utf-8 -*-
"""Chat — DB storage helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException

from ..app_db import db_conn
from ..config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_session(*, user_id: str, agent_id: str, title: str) -> Dict[str, Any]:
    session_id = str(uuid4())
    now = _utc_now()
    with db_conn(settings.app_db_path) as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions (id, user_id, agent_id, title, opencode_session_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, NULL, ?, ?)
            """,
            (session_id, user_id, agent_id, title, now, now),
        )
    return {
        "id": session_id,
        "user_id": user_id,
        "agent_id": agent_id,
        "title": title,
        "opencode_session_id": None,
        "created_at": now,
        "updated_at": now,
    }


def list_sessions(*, user_id: str, agent_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    with db_conn(settings.app_db_path) as conn:
        sql = "SELECT * FROM chat_sessions WHERE user_id = ?"
        params: list[Any] = [user_id]
        if agent_id:
            sql += " AND agent_id = ?"
            params.append(agent_id)
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]


def get_session(*, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    with db_conn(settings.app_db_path) as conn:
        row = conn.execute(
            "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def require_session(*, user_id: str, session_id: str) -> Dict[str, Any]:
    row = get_session(user_id=user_id, session_id=session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


def update_session_title_if_first_user_message(*, session_id: str, title: str) -> None:
    with db_conn(settings.app_db_path) as conn:
        # Only update if there is exactly one user message so far (i.e. this is first).
        row = conn.execute(
            "SELECT COUNT(1) AS n FROM chat_messages WHERE session_id = ? AND role = 'user'",
            (session_id,),
        ).fetchone()
        n = int(row["n"]) if row else 0
        if n <= 1:
            conn.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title[:64], _utc_now(), session_id),
            )


def touch_session(*, session_id: str) -> None:
    with db_conn(settings.app_db_path) as conn:
        conn.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (_utc_now(), session_id),
        )


def set_opencode_session_id(*, session_id: str, opencode_session_id: str) -> None:
    with db_conn(settings.app_db_path) as conn:
        conn.execute(
            "UPDATE chat_sessions SET opencode_session_id = ?, updated_at = ? WHERE id = ?",
            (opencode_session_id, _utc_now(), session_id),
        )


def append_message(*, session_id: str, role: str, content: str) -> Dict[str, Any]:
    msg_id = str(uuid4())
    now = _utc_now()
    with db_conn(settings.app_db_path) as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (msg_id, session_id, role, content, now),
        )
        conn.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
    return {"id": msg_id, "session_id": session_id, "role": role, "content": content, "created_at": now}


def list_messages(*, session_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    with db_conn(settings.app_db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
            (session_id, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]


def attach_artifact(*, user_id: str, session_id: str, artifact_id: str) -> None:
    with db_conn(settings.app_db_path) as conn:
        srow = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not srow:
            raise HTTPException(status_code=404, detail="Session not found")
        arow = conn.execute(
            "SELECT id FROM artifacts WHERE id = ? AND user_id = ?",
            (artifact_id, user_id),
        ).fetchone()
        if not arow:
            raise HTTPException(status_code=404, detail="Artifact not found")
        conn.execute(
            "INSERT OR IGNORE INTO session_artifacts (session_id, artifact_id, created_at) VALUES (?, ?, ?)",
            (session_id, artifact_id, _utc_now()),
        )
        conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (_utc_now(), session_id))


def detach_artifact(*, user_id: str, session_id: str, artifact_id: str) -> None:
    with db_conn(settings.app_db_path) as conn:
        srow = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not srow:
            raise HTTPException(status_code=404, detail="Session not found")
        conn.execute(
            "DELETE FROM session_artifacts WHERE session_id = ? AND artifact_id = ?",
            (session_id, artifact_id),
        )
        conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (_utc_now(), session_id))


def list_attached_artifacts(*, user_id: str, session_id: str) -> List[Dict[str, Any]]:
    with db_conn(settings.app_db_path) as conn:
        srow = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not srow:
            raise HTTPException(status_code=404, detail="Session not found")
        rows = conn.execute(
            """
            SELECT a.* FROM session_artifacts sa
            JOIN artifacts a ON a.id = sa.artifact_id
            WHERE sa.session_id = ? AND a.user_id = ?
            ORDER BY sa.created_at DESC
            """,
            (session_id, user_id),
        ).fetchall()
        return [dict(r) for r in rows]

