# -*- coding: utf-8 -*-
"""Exercise domain aggregation (steps + workouts)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import ExerciseDay, ExerciseSummaryResponse

from ..config import settings


def _root(user_id: str) -> Path:
    return settings.data_root / "users" / user_id / "healthkit"


def _date_prefix(iso8601: str) -> str:
    return (iso8601 or "")[:10]


def _iter_days(start: str, end: str) -> List[str]:
    try:
        s = datetime.fromisoformat(start).date()
        e = datetime.fromisoformat(end).date()
    except Exception:
        return []
    if e < s:
        return []
    days: List[str] = []
    cur = s
    while cur <= e:
        days.append(cur.isoformat())
        cur = cur + timedelta(days=1)
    return days


def _iter_payloads(user_id: str, device_id: str) -> Iterable[Dict[str, Any]]:
    device_dir = _root(user_id) / device_id
    if not device_dir.exists():
        return []
    payloads: List[Dict[str, Any]] = []
    for fp in sorted(device_dir.glob("*.json")):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
            payload = record.get("data") or {}
            payload["_meta_synced_at"] = record.get("synced_at")
            payloads.append(payload)
        except Exception:
            continue
    return payloads


@dataclass
class _Agg:
    steps: int = 0
    workout_energy_kcal: float = 0.0
    workout_count: int = 0


def _aggregate_device(user_id: str, device_id: str, *, start: str, end: str) -> Tuple[List[ExerciseDay], List[str], Optional[str]]:
    days = _iter_days(start, end)
    if not days:
        return [], ["Invalid date range"], None
    day_set = set(days)
    per_day: Dict[str, _Agg] = {d: _Agg() for d in days}
    warnings: List[str] = []
    last_synced_at: Optional[str] = None

    workouts_seen: Dict[str, float] = {}

    for payload in _iter_payloads(user_id, device_id):
        synced_at = payload.get("_meta_synced_at")
        if isinstance(synced_at, str) and (not last_synced_at or synced_at > last_synced_at):
            last_synced_at = synced_at

        for item in payload.get("daily_steps", []) or []:
            try:
                d = str(item.get("date") or "")
                count = int(item.get("count") or 0)
            except Exception:
                continue
            if d not in day_set:
                continue
            per_day[d].steps = max(per_day[d].steps, max(count, 0))

        for w in payload.get("workouts", []) or []:
            try:
                start_time = str(w.get("start_time") or "")
                end_time = str(w.get("end_time") or "")
                activity_type = str(w.get("activity_type") or "other")
                energy = float(w.get("total_energy_kcal") or 0.0)
            except Exception:
                continue
            if not start_time or not end_time:
                continue
            day = _date_prefix(start_time)
            if day not in day_set:
                continue
            token = f"{start_time}|{end_time}|{activity_type}"
            prev = workouts_seen.get(token)
            if prev is None or energy > prev:
                workouts_seen[token] = max(energy, 0.0)

    for token, energy in workouts_seen.items():
        day = _date_prefix(token.split("|", 1)[0])
        if day not in per_day:
            continue
        per_day[day].workout_count += 1
        per_day[day].workout_energy_kcal += energy

    out = []
    for day in days:
        agg = per_day[day]
        out.append(
            ExerciseDay(
                date=day,
                steps=agg.steps,
                workout_energy_kcal=round(agg.workout_energy_kcal, 1),
                workout_count=agg.workout_count,
            )
        )

    return out, warnings, last_synced_at


def get_device_exercise_summary(user_id: str, device_id: str, *, start: str, end: str) -> Dict[str, Any]:
    days, warnings, last_synced_at = _aggregate_device(user_id, device_id, start=start, end=end)
    resp = ExerciseSummaryResponse(
        subject_id=device_id,
        subject_type="device",
        start=start,
        end=end,
        days=days,
        warnings=warnings,
        last_healthkit_sync_at=last_synced_at,
    )
    return resp.model_dump()
