# -*- coding: utf-8 -*-
"""Auth — DB storage helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from ..app_db import db_conn
from ..config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with db_conn(settings.app_db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    with db_conn(settings.app_db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def create_user(*, email: str, password_hash: str) -> Dict[str, Any]:
    user_id = str(uuid4())
    now = _utc_now()
    email_norm = email.lower().strip()
    with db_conn(settings.app_db_path) as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, email_norm, password_hash, now),
        )
    return {"id": user_id, "email": email_norm, "password_hash": password_hash, "created_at": now}

