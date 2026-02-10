# -*- coding: utf-8 -*-
"""LLM-driven plan generation helpers."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Tuple

from fastapi import HTTPException

from ..agent_service import call_agent
from ..artifacts.storage import list_session_artifacts, read_artifact_extracted_text, read_artifact_parsed_json
from ..clinical.models import ClinicalRecordType
from ..clinical.storage import get_subject, latest_record


_EXERCISE_SCHEMA = {
    "title": "string",
    "summary": "string",
    "valid_from": "YYYY-MM-DD",
    "valid_to": "YYYY-MM-DD",
    "goals": {
        "steps_target": "number|null",
        "minutes_target": "number|null",
        "kcal_target": "number|null",
        "hr_zone": "string|null",
    },
    "sessions": [
        {
            "type": "string",
            "duration_min": "number|null",
            "intensity": "string|null",
            "kcal_est": "number|null",
            "notes": "string|null",
        }
    ],
}

_NUTRITION_SCHEMA = {
    "title": "string",
    "summary": "string",
    "valid_from": "YYYY-MM-DD",
    "valid_to": "YYYY-MM-DD",
    "macros": {
        "kcal": "number|null",
        "protein_g": "number|null",
        "carbs_g": "number|null",
        "fat_g": "number|null",
    },
    "meals": [
        {
            "meal_type": "string",
            "kcal": "number|null",
            "foods": ["string"],
        }
    ],
    "constraints": {
        "low_sugar": "boolean|null",
        "low_salt": "boolean|null",
        "high_fiber": "boolean|null",
        "notes": "string|null",
    },
}


def _default_valid_range() -> Tuple[str, str]:
    today = date.today()
    return today.isoformat(), (today + timedelta(days=6)).isoformat()


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found")
    return json.loads(match.group(0))


def _build_context(*, user_id: str, patient_id: str, session_id: str) -> Dict[str, Any]:
    subject = get_subject(patient_id)
    latest_cpet = latest_record(patient_id, ClinicalRecordType.cpet_report)
    artifacts = list_session_artifacts(user_id=user_id, session_id=session_id)
    artifact_items: List[Dict[str, Any]] = []
    for row in artifacts:
        parsed = read_artifact_parsed_json(row)
        extracted = read_artifact_extracted_text(row, max_chars=8000)
        artifact_items.append(
            {
                "id": row.get("id"),
                "category": row.get("category"),
                "filename": row.get("filename"),
                "parsed_json": parsed,
                "extracted_text": extracted,
            }
        )
    return {
        "patient": subject.model_dump() if subject else {"patient_id": patient_id},
        "latest_cpet": latest_cpet.model_dump() if latest_cpet else None,
        "artifacts": artifact_items,
    }


def generate_plan_draft(
    *,
    user_id: str,
    patient_id: str,
    session_id: str,
    plan_type: str,
) -> Dict[str, Any]:
    context = _build_context(user_id=user_id, patient_id=patient_id, session_id=session_id)
    warnings: List[str] = []
    if not context.get("artifacts"):
        warnings.append("未提供可解析的报告或数据，处方基于描述生成")

    schema = _EXERCISE_SCHEMA if plan_type == "exercise" else _NUTRITION_SCHEMA
    plan_title = "运动处方" if plan_type == "exercise" else "营养规划"
    valid_from, valid_to = _default_valid_range()

    system_prompt = (
        "You are a clinical assistant. Generate a plan strictly in JSON. "
        "Do NOT output markdown or extra text. Return a single JSON object with keys: "
        "summary (string), plan (object following schema), warnings (array). "
        "If data is missing, set fields to null and add warning strings."
    )

    user_payload = {
        "task": f"Generate a {plan_type} plan.",
        "schema": schema,
        "defaults": {"valid_from": valid_from, "valid_to": valid_to, "title": plan_title},
        "context": context,
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]

    try:
        result = call_agent(messages)
        content = (
            result.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        parsed = _extract_json(content)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Plan generation failed: {exc}") from exc

    summary = parsed.get("summary") or ""
    plan = parsed.get("plan") or {}
    warnings.extend(parsed.get("warnings") or [])

    if not isinstance(plan, dict):
        raise HTTPException(status_code=502, detail="Plan generation returned invalid payload")

    plan.setdefault("title", plan_title)
    plan.setdefault("summary", summary)
    plan.setdefault("valid_from", valid_from)
    plan.setdefault("valid_to", valid_to)

    if plan_type == "exercise":
        plan.setdefault("goals", {})
        plan.setdefault("sessions", [])
    else:
        plan.setdefault("macros", {})
        plan.setdefault("meals", [])
        plan.setdefault("constraints", {})

    if not summary:
        summary = plan.get("summary") or plan_title

    return {"summary": summary, "payload": plan, "warnings": warnings, "context": context}
