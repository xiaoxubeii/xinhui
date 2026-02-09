# -*- coding: utf-8 -*-
"""API keys — DB storage helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from ..app_db import db_conn
from ..config import settings

_KEY_PREFIX = "xinhui_"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_api_key(api_key: str) -> str:
    secret = (settings.api_key_secret or settings.jwt_secret).encode("utf-8")
    digest = hmac.new(secret, api_key.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def _generate_api_key() -> Tuple[str, str, str]:
    raw = secrets.token_urlsafe(32)
    full = f"{_KEY_PREFIX}{raw}"
    prefix = full[:12]
    key_hash = _hash_api_key(full)
    return full, prefix, key_hash


def create_api_key(*, user_id: str, name: Optional[str]) -> Tuple[Dict[str, Any], str]:
    key_id = str(uuid4())
    now = _utc_now()
    full_key, prefix, key_hash = _generate_api_key()
    with db_conn(settings.app_db_path) as conn:
        conn.execute(
            """
            INSERT INTO api_keys (id, user_id, name, prefix, key_hash, created_at, last_used_at, revoked_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
            """,
            (key_id, user_id, name, prefix, key_hash, now),
        )
    row = {
        "id": key_id,
        "user_id": user_id,
        "name": name,
        "prefix": prefix,
        "key_hash": key_hash,
        "created_at": now,
        "last_used_at": None,
        "revoked_at": None,
    }
    return row, full_key


def list_api_keys(*, user_id: str) -> list[Dict[str, Any]]:
    with db_conn(settings.app_db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, name, prefix, created_at, last_used_at, revoked_at
            FROM api_keys
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def revoke_api_key(*, user_id: str, key_id: str) -> bool:
    now = _utc_now()
    with db_conn(settings.app_db_path) as conn:
        cur = conn.execute(
            """
            UPDATE api_keys
            SET revoked_at = ?
            WHERE id = ? AND user_id = ? AND revoked_at IS NULL
            """,
            (now, key_id, user_id),
        )
        return cur.rowcount > 0


def lookup_api_key(api_key: str) -> Optional[Tuple[Dict[str, Any], str]]:
    key_hash = _hash_api_key(api_key)
    with db_conn(settings.app_db_path) as conn:
        row = conn.execute(
            """
            SELECT ak.id AS api_key_id, ak.user_id, u.id AS user_id_real, u.email, u.password_hash, u.created_at
            FROM api_keys ak
            JOIN users u ON u.id = ak.user_id
            WHERE ak.key_hash = ? AND ak.revoked_at IS NULL
            """,
            (key_hash,),
        ).fetchone()
        if not row:
            return None
        # Update last used timestamp.
        conn.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (_utc_now(), row["api_key_id"]))
        user_row = {
            "id": row["user_id_real"],
            "email": row["email"],
            "password_hash": row["password_hash"],
            "created_at": row["created_at"],
        }
        return user_row, row["api_key_id"]

