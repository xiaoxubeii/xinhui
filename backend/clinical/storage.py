# -*- coding: utf-8 -*-
"""Clinical records — JSON file storage."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from .models import (
    ClinicalRecord,
    ClinicalRecordCreateRequest,
    ClinicalRecordType,
    ClinicalSubject,
    ClinicalSubjectUpsertRequest,
)

_DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "clinical"
_SUBJECTS_DIR = _DATA_ROOT / "subjects"
_RECORDS_DIR = _DATA_ROOT / "records"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_key(value: str) -> str:
    # Keep it filesystem-safe without changing semantics too much.
    # Replace path separators and any unusual characters.
    cleaned = re.sub(r"[^\w.\-@]+", "_", value.strip())
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    if cleaned in {"", ".", ".."}:
        cleaned = "unknown"
    return cleaned[:200]


def _iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def upsert_subject(request: ClinicalSubjectUpsertRequest) -> ClinicalSubject:
    _ensure_dir(_SUBJECTS_DIR)
    key = _safe_key(request.patient_id)
    fp = _SUBJECTS_DIR / f"{key}.json"
    now = _iso_now()
    if fp.exists():
        try:
            existing = ClinicalSubject.model_validate(json.loads(fp.read_text(encoding="utf-8")))
            created_at = existing.created_at
        except Exception:
            created_at = now
    else:
        created_at = now

    subject = ClinicalSubject(
        patient_id=request.patient_id,
        name=request.name,
        sex=request.sex,
        age=request.age,
        height_cm=request.height_cm,
        weight_kg=request.weight_kg,
        diagnosis=request.diagnosis,
        linked_device_ids=request.linked_device_ids,
        notes=request.notes,
        created_at=created_at,
        updated_at=now,
    )
    fp.write_text(subject.model_dump_json(ensure_ascii=False, indent=2), encoding="utf-8")
    return subject


def get_subject(patient_id: str) -> Optional[ClinicalSubject]:
    key = _safe_key(patient_id)
    fp = _SUBJECTS_DIR / f"{key}.json"
    if not fp.exists():
        return None
    try:
        return ClinicalSubject.model_validate(json.loads(fp.read_text(encoding="utf-8")))
    except Exception:
        return None


def list_subjects(limit: int = 100, offset: int = 0) -> List[ClinicalSubject]:
    if not _SUBJECTS_DIR.exists():
        return []
    items: List[ClinicalSubject] = []
    for fp in sorted(_SUBJECTS_DIR.glob("*.json"), reverse=True):
        try:
            items.append(ClinicalSubject.model_validate(json.loads(fp.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return items[offset : offset + limit]


def _patient_records_dir(patient_id: str) -> Path:
    return _RECORDS_DIR / _safe_key(patient_id)


def create_record(request: ClinicalRecordCreateRequest) -> ClinicalRecord:
    patient_dir = _patient_records_dir(request.patient_id)
    _ensure_dir(patient_dir)
    record_id = str(uuid4())
    record = ClinicalRecord(
        record_id=record_id,
        patient_id=request.patient_id,
        record_type=request.record_type,
        recorded_at=request.recorded_at,
        title=request.title,
        tags=request.tags,
        source=request.source,
        data=request.data,
        created_at=_iso_now(),
    )
    fp = patient_dir / f"{record_id}.json"
    fp.write_text(record.model_dump_json(ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def get_record(patient_id: str, record_id: str) -> Optional[ClinicalRecord]:
    fp = _patient_records_dir(patient_id) / f"{record_id}.json"
    if not fp.exists():
        return None
    try:
        return ClinicalRecord.model_validate(json.loads(fp.read_text(encoding="utf-8")))
    except Exception:
        return None


def delete_record(patient_id: str, record_id: str) -> bool:
    fp = _patient_records_dir(patient_id) / f"{record_id}.json"
    if not fp.exists():
        return False
    try:
        fp.unlink()
        return True
    except Exception:
        return False


def _date_prefix(iso8601: str) -> str:
    return (iso8601 or "")[:10]


def list_records(
    patient_id: str,
    *,
    record_type: ClinicalRecordType | None = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[ClinicalRecord]:
    patient_dir = _patient_records_dir(patient_id)
    if not patient_dir.exists():
        return []

    start_date = start or "0000-01-01"
    end_date = end or "9999-12-31"

    records: List[ClinicalRecord] = []
    for fp in sorted(patient_dir.glob("*.json"), reverse=True):
        try:
            rec = ClinicalRecord.model_validate(json.loads(fp.read_text(encoding="utf-8")))
        except Exception:
            continue
        if record_type and rec.record_type != record_type:
            continue
        d = _date_prefix(rec.recorded_at)
        if not (start_date <= d <= end_date):
            continue
        records.append(rec)

    return records[offset : offset + limit]


def latest_record(patient_id: str, record_type: ClinicalRecordType) -> Optional[ClinicalRecord]:
    items = list_records(patient_id, record_type=record_type, limit=1, offset=0)
    return items[0] if items else None

