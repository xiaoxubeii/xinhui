# -*- coding: utf-8 -*-
"""Plan storage helpers (SQLite)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

from fastapi import HTTPException

from ..app_db import db_conn
from ..config import settings


def _iso_now() -> str:
    return datetime.utcnow().isoformat()


def _safe_date(value: Any) -> Optional[str]:
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return None


def _row_to_plan(row: Dict[str, Any]) -> Dict[str, Any]:
    payload = {}
    raw = row.get("payload_json")
    if raw:
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
    return {
        "plan_id": row.get("id"),
        "plan_type": row.get("plan_type"),
        "summary": row.get("summary") or "",
        "payload": payload,
        "status": row.get("status"),
        "confirmed_at": row.get("confirmed_at"),
        "valid_from": row.get("valid_from"),
        "valid_to": row.get("valid_to"),
    }


def create_plan_draft(
    *,
    user_id: str,
    patient_id: str,
    plan_type: str,
    payload: Dict[str, Any],
    summary: str,
    source_session_id: str,
    source_artifact_ids: Iterable[str] | None = None,
) -> Dict[str, Any]:
    plan_id = str(uuid4())
    now = _iso_now()
    payload_json = json.dumps(payload, ensure_ascii=False)
    valid_from = _safe_date(payload.get("valid_from"))
    valid_to = _safe_date(payload.get("valid_to"))
    artifact_ids = list(source_artifact_ids or [])

    with db_conn(settings.app_db_path) as conn:
        conn.execute(
            """
            INSERT INTO plans (
                id, user_id, patient_id, plan_type, status, summary, payload_json,
                valid_from, valid_to, source_session_id, source_artifact_ids, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id,
                user_id,
                patient_id,
                plan_type,
                "draft",
                summary,
                payload_json,
                valid_from,
                valid_to,
                source_session_id,
                json.dumps(artifact_ids, ensure_ascii=False),
                now,
            ),
        )

    return {
        "plan_id": plan_id,
        "plan_type": plan_type,
        "summary": summary,
        "payload": payload,
        "status": "draft",
        "confirmed_at": None,
        "valid_from": valid_from,
        "valid_to": valid_to,
    }


def confirm_plan(*, user_id: str, draft_id: str) -> Dict[str, Any]:
    now = _iso_now()
    with db_conn(settings.app_db_path) as conn:
        row = conn.execute(
            "SELECT * FROM plans WHERE id = ? AND user_id = ?",
            (draft_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Plan not found")

        current = dict(row)
        status = current.get("status")
        if status == "confirmed":
            return _row_to_plan(current)
        if status != "draft":
            raise HTTPException(status_code=409, detail="Plan already confirmed")

        raw_payload = current.get("payload_json") or ""
        try:
            payload = json.loads(raw_payload) if raw_payload else {}
        except Exception:
            payload = {}

        plan_type = current.get("plan_type")
        if plan_type == "exercise":
            payload["title"] = "运动规划"
        elif plan_type == "nutrition":
            payload["title"] = "营养规划"

        summary = payload.get("summary") or current.get("summary") or payload.get("title") or ""
        payload["summary"] = summary

        valid_from = _safe_date(payload.get("valid_from")) or current.get("valid_from")
        valid_to = _safe_date(payload.get("valid_to")) or current.get("valid_to")

        confirmed_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO plans (
                id, user_id, patient_id, plan_type, status, summary, payload_json,
                valid_from, valid_to, source_session_id, source_artifact_ids, created_at, confirmed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                confirmed_id,
                user_id,
                current.get("patient_id"),
                plan_type,
                "confirmed",
                summary,
                json.dumps(payload, ensure_ascii=False),
                valid_from,
                valid_to,
                current.get("source_session_id"),
                current.get("source_artifact_ids"),
                now,
                now,
            ),
        )
        conn.execute(
            "UPDATE plans SET status = ? WHERE id = ?",
            ("archived", draft_id),
        )

        confirmed_row = conn.execute(
            "SELECT * FROM plans WHERE id = ? AND user_id = ?",
            (confirmed_id, user_id),
        ).fetchone()

    return _row_to_plan(dict(confirmed_row))


def _within_date(date: Optional[str], valid_from: Optional[str], valid_to: Optional[str]) -> bool:
    if not date:
        return True
    if valid_from and date < valid_from:
        return False
    if valid_to and date > valid_to:
        return False
    return True


def get_latest_confirmed_plan(
    *,
    user_id: str,
    patient_id: str,
    plan_type: str,
    date: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    with db_conn(settings.app_db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM plans
            WHERE user_id = ? AND patient_id = ? AND plan_type = ? AND status = 'confirmed'
            ORDER BY confirmed_at DESC, created_at DESC
            """,
            (user_id, patient_id, plan_type),
        ).fetchall()

    for row in rows:
        r = dict(row)
        if _within_date(date, r.get("valid_from"), r.get("valid_to")):
            return _row_to_plan(r)

    if rows:
        return _row_to_plan(dict(rows[0]))
    return None


def list_plans_by_session(
    *,
    user_id: str,
    session_id: str,
    status: Optional[str] = None,
    plan_type: Optional[str] = None,
) -> list[Dict[str, Any]]:
    sql = """
        SELECT * FROM plans
        WHERE user_id = ? AND source_session_id = ?
    """
    params: list[Any] = [user_id, session_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if plan_type:
        sql += " AND plan_type = ?"
        params.append(plan_type)
    sql += " ORDER BY created_at DESC"

    with db_conn(settings.app_db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_plan(dict(r)) for r in rows]
