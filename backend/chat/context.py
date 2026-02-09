# -*- coding: utf-8 -*-
"""Chat context assembly.

Builds the JSON context passed to OpenCode/Qwen based on:
- current user (personal mode: patient_id == user_id)
- active agent/entry (report/analysis/health/diet)
- session attached artifacts
- recent artifacts from the user's library (auto-included)
- recent lifestyle summaries (HealthKit + Diet)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional

from ..artifacts.storage import (
    get_artifact_row,
    list_artifacts,
    read_artifact_extracted_text,
    read_artifact_parsed_json,
)
from ..clinical.models import ClinicalRecordType
from ..clinical.storage import get_subject, latest_record
from ..lifestyle.storage import get_patient_lifestyle_summary
from .storage import list_attached_artifacts


def _is_plain_dict(value: Any) -> bool:
    return isinstance(value, dict)


def _flatten_record(record: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = dict(record)
    for value in record.values():
        if not _is_plain_dict(value):
            continue
        for k, v in value.items():
            if _is_plain_dict(v):
                for dk, dv in v.items():
                    result[dk] = dv
            else:
                result[k] = v
    return result


def _merge_parsed_results(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for row in rows:
        parsed = read_artifact_parsed_json(row)
        if not parsed or not isinstance(parsed, dict):
            continue
        merged.update(_flatten_record(parsed))
    return merged


def _auto_categories(agent_id: str) -> List[str]:
    if agent_id == "report":
        return ["cpet_report", "lab_report", "imaging_report"]
    if agent_id == "analysis":
        return ["exercise_data", "cpet_report", "health_data"]
    if agent_id == "health":
        return ["health_data", "cpet_report", "lab_report"]
    if agent_id == "diet":
        return ["diet_data"]
    return ["other"]


def _domain_id_for_agent(agent_id: str) -> str:
    if agent_id in {"report", "clinical", "prescription"}:
        return "clinical"
    if agent_id == "analysis":
        return "exercise"
    if agent_id == "health":
        return "health"
    if agent_id == "diet":
        return "nutrition"
    return "clinical"


def _date_range_last_days(days: int) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=max(0, days - 1))
    return start.isoformat(), end.isoformat()


def build_agent_context(
    *,
    user_id: str,
    agent_id: str,
    session_id: str,
    extra_artifact_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    attached = list_attached_artifacts(user_id=user_id, session_id=session_id)
    selected: List[Dict[str, Any]] = list(attached)
    seen = {r["id"] for r in selected if r.get("id")}

    # Extra attachments for this turn (do not persist attach unless client calls attach endpoint).
    for aid in extra_artifact_ids or []:
        if aid in seen:
            continue
        row = get_artifact_row(user_id=user_id, artifact_id=aid)
        if row:
            selected.append(row)
            seen.add(aid)

    # Auto-include recent artifacts by category (small cap to keep context bounded).
    for cat in _auto_categories(agent_id):
        rows = list_artifacts(user_id=user_id, category=cat, limit=3, offset=0)
        for r in rows:
            if r["id"] in seen:
                continue
            selected.append(r)
            seen.add(r["id"])

    # Hard cap: keep most recent 8 artifacts in context.
    selected = sorted(selected, key=lambda r: r.get("created_at") or "", reverse=True)[:8]

    files = [
        {
            "id": r["id"],
            "category": r.get("category"),
            "title": r.get("title"),
            "name": r.get("filename"),
            "type": r.get("content_type"),
            "size": r.get("size_bytes"),
            "has_parsed_json": bool(r.get("parsed_json_relpath")),
            "has_extracted_text": bool(r.get("extracted_text_relpath")),
            "created_at": r.get("created_at"),
        }
        for r in selected
    ]
    raw_texts = []
    for r in selected:
        text = read_artifact_extracted_text(r, max_chars=8000)
        if text:
            raw_texts.append({"name": r.get("filename"), "text": text})

    cpet_results = _merge_parsed_results(selected)

    # Patient/clinical context (personal-mode: patient_id=user_id).
    subject = get_subject(user_id)
    latest_cpet = latest_record(user_id, ClinicalRecordType.cpet_report)
    start, end = _date_range_last_days(30)
    lifestyle = None
    try:
        lifestyle = get_patient_lifestyle_summary(user_id, user_id, start=start, end=end, device="all", merge="sum")
    except Exception:
        lifestyle = None

    clinical_context = {
        "patient": subject.model_dump() if subject else {"patient_id": user_id},
        "latest_cpet": latest_cpet.model_dump() if latest_cpet else None,
        "linked_device_ids": (subject.linked_device_ids if subject else []),
        "lifestyle": lifestyle,
    }

    return {
        "agent_id": agent_id,
        "domain_id": _domain_id_for_agent(agent_id),
        "patient_id": user_id,
        "clinical_context": clinical_context,
        "lifestyle_summary": lifestyle,
        "cpet_results": cpet_results,
        "files": files,
        "raw_texts": raw_texts,
        "output_format": "markdown",
    }

