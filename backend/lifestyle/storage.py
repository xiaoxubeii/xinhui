# -*- coding: utf-8 -*-
"""Lifestyle aggregation — reads stored healthkit/diet JSON files and aggregates by day."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import LifestyleDay, LifestyleSummaryResponse, LifestyleTotals

from ..config import settings


def _healthkit_root(user_id: str) -> Path:
    return settings.data_root / "users" / user_id / "healthkit"


def _diet_root(user_id: str) -> Path:
    return settings.data_root / "users" / user_id / "diet"


def _date_prefix(iso8601: str) -> str:
    return (iso8601 or "")[:10]


def _parse_iso(iso8601: str) -> Optional[datetime]:
    if not iso8601:
        return None
    # Handle trailing Z.
    value = iso8601.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _iter_healthkit_payloads(user_id: str, device_id: str) -> Iterable[Dict[str, Any]]:
    device_dir = _healthkit_root(user_id) / device_id
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


def _iter_diet_entries(user_id: str, device_id: str) -> Iterable[Dict[str, Any]]:
    device_dir = _diet_root(user_id) / device_id
    if not device_dir.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for fp in sorted(device_dir.glob("*.json")):
        try:
            entries.append(json.loads(fp.read_text(encoding="utf-8")))
        except Exception:
            continue
    return entries


@dataclass
class _WorkoutKey:
    start_time: str
    end_time: str
    activity_type: str

    @property
    def day(self) -> str:
        return _date_prefix(self.start_time)

    @property
    def token(self) -> str:
        return f"{self.start_time}|{self.end_time}|{self.activity_type}"


def _aggregate_healthkit(user_id: str, device_id: str) -> Tuple[Dict[str, Dict[str, Any]], List[str], Optional[str]]:
    per_day: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []
    last_synced_at: Optional[str] = None

    # De-dupe maps.
    workouts_seen: Dict[str, float] = {}
    sleep_seen: Dict[str, float] = {}

    for payload in _iter_healthkit_payloads(user_id, device_id):
        synced_at = payload.get("_meta_synced_at")
        if isinstance(synced_at, str):
            if not last_synced_at or synced_at > last_synced_at:
                last_synced_at = synced_at

        # Steps snapshot: take max per date.
        for item in payload.get("daily_steps", []) or []:
            try:
                d = str(item.get("date"))
                count = int(item.get("count") or 0)
            except Exception:
                continue
            if not d:
                continue
            day = per_day.setdefault(d, {})
            day["steps"] = max(int(day.get("steps") or 0), max(count, 0))

        # Workouts: de-duplicate by (start,end,activity), energy take max.
        for w in payload.get("workouts", []) or []:
            try:
                start_time = str(w.get("start_time") or "")
                end_time = str(w.get("end_time") or "")
                activity_type = str(w.get("activity_type") or "other")
                key = _WorkoutKey(start_time=start_time, end_time=end_time, activity_type=activity_type)
                energy = float(w.get("total_energy_kcal") or 0.0)
            except Exception:
                continue
            if not key.start_time or not key.end_time:
                continue
            token = key.token
            prev = workouts_seen.get(token)
            if prev is None or energy > prev:
                workouts_seen[token] = max(energy, 0.0)

        # Sleep: only core/deep/rem; de-duplicate by (start,end,stage).
        for s in payload.get("sleep_sessions", []) or []:
            try:
                start_time = str(s.get("start_time") or "")
                end_time = str(s.get("end_time") or "")
                stage = str(s.get("stage") or "")
            except Exception:
                continue
            if stage not in {"core", "deep", "rem"}:
                continue
            start_dt = _parse_iso(start_time)
            end_dt = _parse_iso(end_time)
            if not start_dt or not end_dt:
                continue
            seconds = (end_dt - start_dt).total_seconds()
            if seconds <= 0:
                continue
            token = f"{start_time}|{end_time}|{stage}"
            hours = seconds / 3600.0
            prev = sleep_seen.get(token)
            if prev is None or hours > prev:
                sleep_seen[token] = hours

    # Materialize workouts/sleep into per-day.
    workout_count_per_day: Dict[str, int] = {}
    workout_energy_per_day: Dict[str, float] = {}
    for token, energy in workouts_seen.items():
        # token is start|end|activity
        parts = token.split("|", 2)
        if not parts:
            continue
        day = _date_prefix(parts[0])
        workout_count_per_day[day] = workout_count_per_day.get(day, 0) + 1
        workout_energy_per_day[day] = workout_energy_per_day.get(day, 0.0) + energy

    sleep_hours_per_day: Dict[str, float] = {}
    for token, hours in sleep_seen.items():
        start_time = token.split("|", 1)[0]
        day = _date_prefix(start_time)
        sleep_hours_per_day[day] = sleep_hours_per_day.get(day, 0.0) + hours

    for day, count in workout_count_per_day.items():
        per_day.setdefault(day, {})["workout_count"] = count
    for day, kcal in workout_energy_per_day.items():
        per_day.setdefault(day, {})["workout_energy_kcal"] = round(kcal, 1)
    for day, hours in sleep_hours_per_day.items():
        per_day.setdefault(day, {})["sleep_hours"] = round(hours, 2)

    return per_day, warnings, last_synced_at


def _aggregate_diet(user_id: str, device_id: str) -> Tuple[Dict[str, Dict[str, Any]], List[str], Optional[str]]:
    per_day: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []
    last_entry_at: Optional[str] = None

    for entry in _iter_diet_entries(user_id, device_id):
        try:
            eaten_at = str(entry.get("eaten_at") or "")
            totals = entry.get("totals") or {}
            kcal = float(totals.get("calories_kcal") or 0.0)
        except Exception:
            continue
        day = _date_prefix(eaten_at)
        if not day:
            continue
        if eaten_at and (not last_entry_at or eaten_at > last_entry_at):
            last_entry_at = eaten_at
        bucket = per_day.setdefault(day, {})
        bucket["diet_entry_count"] = int(bucket.get("diet_entry_count") or 0) + 1
        bucket["diet_intake_kcal"] = round(float(bucket.get("diet_intake_kcal") or 0.0) + max(kcal, 0.0), 1)

    return per_day, warnings, last_entry_at


def _iter_days_safe(start: str, end: str) -> List[str]:
    try:
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)
    except Exception:
        return []
    if e < s:
        return []
    days: List[str] = []
    cur = s.date()
    end_d = e.date()
    while cur <= end_d:
        days.append(cur.isoformat())
        cur = cur + timedelta(days=1)
    return days


def get_device_lifestyle_summary(user_id: str, device_id: str, *, start: str, end: str) -> Dict[str, Any]:
    hk_per_day, hk_warnings, last_hk = _aggregate_healthkit(user_id, device_id)
    diet_per_day, diet_warnings, last_diet = _aggregate_diet(user_id, device_id)

    warnings = hk_warnings + diet_warnings
    days: List[LifestyleDay] = []

    totals = LifestyleTotals()

    for day in _iter_days_safe(start, end):
        steps = int(hk_per_day.get(day, {}).get("steps") or 0)
        workout_kcal = float(hk_per_day.get(day, {}).get("workout_energy_kcal") or 0.0)
        workout_count = int(hk_per_day.get(day, {}).get("workout_count") or 0)
        sleep_hours = float(hk_per_day.get(day, {}).get("sleep_hours") or 0.0)
        diet_kcal = float(diet_per_day.get(day, {}).get("diet_intake_kcal") or 0.0)
        diet_count = int(diet_per_day.get(day, {}).get("diet_entry_count") or 0)
        net = round(diet_kcal - workout_kcal, 1)

        days.append(
            LifestyleDay(
                date=day,
                steps=steps,
                workout_energy_kcal=round(workout_kcal, 1),
                workout_count=workout_count,
                sleep_hours=round(sleep_hours, 2),
                diet_intake_kcal=round(diet_kcal, 1),
                diet_entry_count=diet_count,
                net_kcal=net,
            )
        )

        totals.steps += steps
        totals.workout_energy_kcal += workout_kcal
        totals.workout_count += workout_count
        totals.sleep_hours += sleep_hours
        totals.diet_intake_kcal += diet_kcal
        totals.diet_entry_count += diet_count

    totals.workout_energy_kcal = round(totals.workout_energy_kcal, 1)
    totals.diet_intake_kcal = round(totals.diet_intake_kcal, 1)
    totals.net_kcal = round(totals.diet_intake_kcal - totals.workout_energy_kcal, 1)
    totals.sleep_hours = round(totals.sleep_hours, 2)

    resp = LifestyleSummaryResponse(
        device_id=device_id,
        start=start,
        end=end,
        days=days,
        totals=totals,
        warnings=warnings,
        last_healthkit_sync_at=last_hk,
        last_diet_entry_at=last_diet,
    )
    return resp.model_dump()


def get_patient_lifestyle_summary(
    user_id: str,
    patient_id: str,
    *,
    start: str,
    end: str,
    device: str = "all",
    merge: str = "sum",
) -> Dict[str, Any]:
    """Merge lifestyle summaries across devices linked to a patient.

    Note:
    - `merge=sum` may double-count if multiple device_ids read the same HealthKit account.
      Web UI should allow filtering a specific device_id when needed.
    """
    try:
        from ..clinical.storage import get_subject
    except Exception:
        subject = None
    else:
        subject = get_subject(patient_id)

    device_ids: List[str] = []
    if subject and getattr(subject, "linked_device_ids", None):
        device_ids = list(subject.linked_device_ids)
    if device != "all":
        device_ids = [device]

    day_map: Dict[str, LifestyleDay] = {d: LifestyleDay(date=d) for d in _iter_days_safe(start, end)}
    warnings: List[str] = []
    last_hk: Optional[str] = None
    last_diet: Optional[str] = None

    if not device_ids:
        warnings.append("No linked devices for patient")
    else:
        for device_id in device_ids:
            summary = LifestyleSummaryResponse.model_validate(get_device_lifestyle_summary(user_id, device_id, start=start, end=end))
            warnings.extend(summary.warnings)
            if summary.last_healthkit_sync_at and (not last_hk or summary.last_healthkit_sync_at > last_hk):
                last_hk = summary.last_healthkit_sync_at
            if summary.last_diet_entry_at and (not last_diet or summary.last_diet_entry_at > last_diet):
                last_diet = summary.last_diet_entry_at

            for day in summary.days:
                bucket = day_map.setdefault(day.date, LifestyleDay(date=day.date))
                if merge == "max":
                    bucket.steps = max(bucket.steps, day.steps)
                    bucket.workout_energy_kcal = max(bucket.workout_energy_kcal, day.workout_energy_kcal)
                    bucket.workout_count = max(bucket.workout_count, day.workout_count)
                    bucket.sleep_hours = max(bucket.sleep_hours, day.sleep_hours)
                    bucket.diet_intake_kcal = max(bucket.diet_intake_kcal, day.diet_intake_kcal)
                    bucket.diet_entry_count = max(bucket.diet_entry_count, day.diet_entry_count)
                else:
                    bucket.steps += day.steps
                    bucket.workout_energy_kcal += day.workout_energy_kcal
                    bucket.workout_count += day.workout_count
                    bucket.sleep_hours += day.sleep_hours
                    bucket.diet_intake_kcal += day.diet_intake_kcal
                    bucket.diet_entry_count += day.diet_entry_count
                bucket.net_kcal = round(bucket.diet_intake_kcal - bucket.workout_energy_kcal, 1)

    days = [day_map[d] for d in sorted(day_map.keys())]
    totals = LifestyleTotals()
    for day in days:
        totals.steps += day.steps
        totals.workout_energy_kcal += day.workout_energy_kcal
        totals.workout_count += day.workout_count
        totals.sleep_hours += day.sleep_hours
        totals.diet_intake_kcal += day.diet_intake_kcal
        totals.diet_entry_count += day.diet_entry_count

    totals.workout_energy_kcal = round(totals.workout_energy_kcal, 1)
    totals.diet_intake_kcal = round(totals.diet_intake_kcal, 1)
    totals.net_kcal = round(totals.diet_intake_kcal - totals.workout_energy_kcal, 1)
    totals.sleep_hours = round(totals.sleep_hours, 2)

    resp = LifestyleSummaryResponse(
        device_id=patient_id,
        start=start,
        end=end,
        days=days,
        totals=totals,
        warnings=warnings,
        last_healthkit_sync_at=last_hk,
        last_diet_entry_at=last_diet,
    )
    return resp.model_dump()
