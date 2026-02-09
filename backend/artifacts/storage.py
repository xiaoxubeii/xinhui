# -*- coding: utf-8 -*-
"""Artifacts — persist uploads on disk + metadata in SQLite."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from ..app_db import db_conn
from ..config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _user_artifacts_root(user_id: str) -> Path:
    return settings.data_root / "users" / user_id / "artifacts"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if not suffix:
        return ""
    # Keep a conservative suffix to avoid weird filesystem behaviors.
    if len(suffix) > 12:
        return ""
    if not re.fullmatch(r"\.[a-z0-9]+", suffix):
        return ""
    return suffix


def _read_text_file(path: Path, *, max_chars: int = 200_000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            text = path.read_text(encoding="latin-1", errors="ignore")
        except Exception:
            return ""
    if len(text) > max_chars:
        return text[:max_chars]
    return text


def _parse_value(value: str) -> Any:
    trimmed = (value or "").strip()
    if not trimmed:
        return ""
    try:
        numeric = float(trimmed)
        if numeric.is_integer():
            return int(numeric)
        return numeric
    except Exception:
        return trimmed


def _detect_delimiter(line: str) -> str:
    candidates = [",", "\t", ";"]
    best = ","
    best_count = -1
    for ch in candidates:
        count = line.count(ch)
        if count > best_count:
            best_count = count
            best = ch
    return best


def _parse_csv_to_object(text: str) -> Optional[Dict[str, Any]]:
    lines = [ln.strip() for ln in re.split(r"\r?\n", text or "") if ln.strip()]
    if not lines:
        return None
    delimiter = _detect_delimiter(lines[0])
    rows = [[cell.strip() for cell in ln.split(delimiter)] for ln in lines]
    if len(rows) < 2:
        return None
    header = rows[0]
    header_key = ",".join(header).lower()
    key_like = len(header) == 2 and (
        ("key" in header_key) or ("指标" in header_key) or ("项目" in header_key)
    )
    if key_like:
        result: Dict[str, Any] = {}
        for row in rows[1:]:
            key = (row[0] if len(row) > 0 else "").strip()
            if not key:
                continue
            result[key] = _parse_value(row[1] if len(row) > 1 else "")
        return result or None
    first_row = rows[1]
    result = {}
    for idx, key in enumerate(header):
        if not key:
            continue
        result[key] = _parse_value(first_row[idx] if idx < len(first_row) else "")
    return result or None


def _extract_pdf_text(pdf_path: Path, *, max_chars: int = 200_000) -> str:
    try:
        from pypdf import PdfReader  # Lazy import (optional dependency).

        reader = PdfReader(str(pdf_path))
        parts: list[str] = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(parts).strip()
    except Exception:
        return ""
    if len(text) > max_chars:
        return text[:max_chars]
    return text


def _maybe_extract_and_parse(
    *,
    original_path: Path,
    filename: str,
    content_type: str,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    suffix = _safe_suffix(filename)
    is_pdf = suffix == ".pdf" or (content_type or "").lower() == "application/pdf"
    is_json = suffix == ".json" or "json" in (content_type or "").lower()
    is_text = suffix in {".txt", ".csv"} or (content_type or "").lower().startswith("text/")
    is_csv = suffix == ".csv" or "csv" in (content_type or "").lower()

    extracted_text: Optional[str] = None
    parsed_json: Optional[Dict[str, Any]] = None

    if is_pdf:
        extracted_text = _extract_pdf_text(original_path)
        return extracted_text, None

    if is_json:
        raw = _read_text_file(original_path)
        extracted_text = raw[:200_000] if raw else ""
        try:
            data = json.loads(raw) if raw else None
        except Exception:
            data = None
        if isinstance(data, dict):
            parsed_json = data
        elif data is not None:
            parsed_json = {"data": data}
        return extracted_text or None, parsed_json

    if is_text:
        raw = _read_text_file(original_path)
        extracted_text = raw[:200_000] if raw else ""
        if is_csv:
            parsed_json = _parse_csv_to_object(raw)
        return extracted_text or None, parsed_json

    return None, None


def create_artifact_from_upload(
    *,
    user_id: str,
    category: str,
    title: Optional[str],
    upload: UploadFile,
    attach_session_id: Optional[str] = None,
) -> Dict[str, Any]:
    artifact_id = str(uuid4())
    created_at = _utc_now()

    filename = upload.filename or f"upload-{artifact_id}"
    content_type = upload.content_type or "application/octet-stream"
    suffix = _safe_suffix(filename)

    artifact_dir = _user_artifacts_root(user_id) / artifact_id
    _ensure_dir(artifact_dir)

    original_path = artifact_dir / f"original{suffix}"

    sha = hashlib.sha256()
    size = 0
    max_bytes = int(settings.max_upload_mb) * 1024 * 1024
    try:
        with original_path.open("wb") as f:
            while True:
                chunk = upload.file.read(1024 * 256)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status_code=400, detail=f"File too large (> {settings.max_upload_mb} MB)")
                sha.update(chunk)
                f.write(chunk)
    finally:
        try:
            upload.file.close()
        except Exception:
            pass

    sha256 = sha.hexdigest()

    extracted_text, parsed_json = _maybe_extract_and_parse(
        original_path=original_path,
        filename=filename,
        content_type=content_type,
    )

    extracted_rel: Optional[str] = None
    parsed_rel: Optional[str] = None
    if extracted_text:
        extracted_path = artifact_dir / "extracted.txt"
        extracted_path.write_text(extracted_text, encoding="utf-8", errors="ignore")
        extracted_rel = str(extracted_path.relative_to(settings.data_root))
    if parsed_json:
        parsed_path = artifact_dir / "parsed.json"
        parsed_path.write_text(json.dumps(parsed_json, ensure_ascii=False, indent=2), encoding="utf-8")
        parsed_rel = str(parsed_path.relative_to(settings.data_root))

    stored_rel = str(original_path.relative_to(settings.data_root))

    with db_conn(settings.app_db_path) as conn:
        conn.execute(
            """
            INSERT INTO artifacts (
                id, user_id, category, title, filename, content_type, size_bytes, sha256,
                stored_relpath, extracted_text_relpath, parsed_json_relpath, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                user_id,
                category,
                title,
                filename,
                content_type,
                int(size),
                sha256,
                stored_rel,
                extracted_rel,
                parsed_rel,
                created_at,
            ),
        )

        if attach_session_id:
            # Ensure session belongs to user.
            row = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
                (attach_session_id, user_id),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Session not found")
            conn.execute(
                "INSERT OR IGNORE INTO session_artifacts (session_id, artifact_id, created_at) VALUES (?, ?, ?)",
                (attach_session_id, artifact_id, created_at),
            )

    preview = None
    if extracted_text:
        preview = extracted_text[:8000]

    return {
        "id": artifact_id,
        "category": category,
        "title": title,
        "filename": filename,
        "content_type": content_type,
        "size_bytes": int(size),
        "sha256": sha256,
        "stored_relpath": stored_rel,
        "extracted_text_relpath": extracted_rel,
        "parsed_json_relpath": parsed_rel,
        "created_at": created_at,
        "extracted_preview": preview,
        "has_parsed_json": bool(parsed_rel),
    }


def list_artifacts(
    *,
    user_id: str,
    category: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Dict[str, Any]]:
    q_norm = (q or "").strip().lower()
    with db_conn(settings.app_db_path) as conn:
        sql = "SELECT * FROM artifacts WHERE user_id = ?"
        params: list[Any] = [user_id]
        if category:
            sql += " AND category = ?"
            params.append(category)
        if q_norm:
            sql += " AND (lower(filename) LIKE ? OR lower(ifnull(title,'')) LIKE ?)"
            like = f"%{q_norm}%"
            params.extend([like, like])
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]


def get_artifact_row(*, user_id: str, artifact_id: str) -> Optional[Dict[str, Any]]:
    with db_conn(settings.app_db_path) as conn:
        row = conn.execute(
            "SELECT * FROM artifacts WHERE id = ? AND user_id = ?",
            (artifact_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def get_artifact_original_path(row: Dict[str, Any]) -> Path:
    rel = row.get("stored_relpath") or ""
    return settings.data_root / rel


def read_artifact_extracted_text(row: Dict[str, Any], *, max_chars: int = 20_000) -> Optional[str]:
    rel = row.get("extracted_text_relpath") or ""
    if not rel:
        return None
    path = settings.data_root / rel
    if not path.exists():
        return None
    text = _read_text_file(path, max_chars=max_chars)
    return text or None


def read_artifact_parsed_json(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rel = row.get("parsed_json_relpath") or ""
    if not rel:
        return None
    path = settings.data_root / rel
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def delete_artifact(*, user_id: str, artifact_id: str) -> bool:
    row = get_artifact_row(user_id=user_id, artifact_id=artifact_id)
    if not row:
        return False

    # Remove DB row (cascade detaches from sessions).
    with db_conn(settings.app_db_path) as conn:
        conn.execute("DELETE FROM artifacts WHERE id = ? AND user_id = ?", (artifact_id, user_id))

    # Remove files.
    try:
        artifact_dir = _user_artifacts_root(user_id) / artifact_id
        if artifact_dir.exists():
            for fp in artifact_dir.glob("*"):
                try:
                    fp.unlink()
                except Exception:
                    pass
            try:
                artifact_dir.rmdir()
            except Exception:
                pass
    except Exception:
        pass
    return True


def list_session_artifacts(*, user_id: str, session_id: str) -> list[Dict[str, Any]]:
    with db_conn(settings.app_db_path) as conn:
        row = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if not row:
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
