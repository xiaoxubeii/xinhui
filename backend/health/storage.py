# -*- coding: utf-8 -*-
"""Health domain aggregation.

Reads stored HealthKit sync JSON files and computes day-level summaries for:
- sleep (core/deep/rem hours)
- resting heart rate (daily average)
- heart rate (daily avg/max)
- SpO2 (daily average)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import HealthDay, HealthSummaryResponse

from ..config import settings


def _root(user_id: str) -> Path:
    return settings.data_root / "users" / user_id / "healthkit"


def _date_prefix(iso8601: str) -> str:
    return (iso8601 or "")[:10]


def _parse_iso(iso8601: str) -> Optional[datetime]:
    if not iso8601:
        return None
    value = iso8601.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


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
class _DayAgg:
    sleep_hours: float = 0.0
    resting_hr_sum: float = 0.0
    resting_hr_count: int = 0
    hr_sum: float = 0.0
    hr_count: int = 0
    hr_max: float = 0.0
    spo2_sum: float = 0.0
    spo2_count: int = 0


def _aggregate_device(user_id: str, device_id: str, *, start: str, end: str) -> Tuple[List[HealthDay], List[str], Optional[str]]:
    days = _iter_days(start, end)
    if not days:
        return [], ["Invalid date range"], None

    day_set = set(days)
    per_day: Dict[str, _DayAgg] = {d: _DayAgg() for d in days}
    warnings: List[str] = []
    last_synced_at: Optional[str] = None

    sleep_seen: Dict[str, float] = {}
    resting_seen: set[str] = set()
    hr_seen: set[str] = set()
    spo2_seen: set[str] = set()

    for payload in _iter_payloads(user_id, device_id):
        synced_at = payload.get("_meta_synced_at")
        if isinstance(synced_at, str) and (not last_synced_at or synced_at > last_synced_at):
            last_synced_at = synced_at

        # Sleep: only core/deep/rem.
        for s in payload.get("sleep_sessions", []) or []:
            try:
                start_time = str(s.get("start_time") or "")
                end_time = str(s.get("end_time") or "")
                stage = str(s.get("stage") or "")
            except Exception:
                continue
            if stage not in {"core", "deep", "rem"}:
                continue
            day = _date_prefix(start_time)
            if day not in day_set:
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

        # Resting HR: de-duplicate by (date|bpm) to avoid double-count from multiple syncs.
        for r in payload.get("resting_heart_rates", []) or []:
            try:
                day = str(r.get("date") or "")
                bpm = float(r.get("bpm") or 0.0)
            except Exception:
                continue
            if day not in day_set:
                continue
            token = f"{day}|{bpm:.3f}"
            if token in resting_seen:
                continue
            resting_seen.add(token)
            per_day[day].resting_hr_sum += max(bpm, 0.0)
            per_day[day].resting_hr_count += 1

        # HR samples: de-duplicate by timestamp.
        for h in payload.get("heart_rate_samples", []) or []:
            try:
                ts = str(h.get("timestamp") or "")
                bpm = float(h.get("bpm") or 0.0)
            except Exception:
                continue
            day = _date_prefix(ts)
            if day not in day_set:
                continue
            if ts in hr_seen:
                continue
            hr_seen.add(ts)
            per_day[day].hr_sum += max(bpm, 0.0)
            per_day[day].hr_count += 1
            per_day[day].hr_max = max(per_day[day].hr_max, bpm)

        # SpO2: de-duplicate by timestamp.
        for o in payload.get("spo2_readings", []) or []:
            try:
                ts = str(o.get("timestamp") or "")
                pct = float(o.get("percentage") or 0.0)
            except Exception:
                continue
            day = _date_prefix(ts)
            if day not in day_set:
                continue
            if ts in spo2_seen:
                continue
            spo2_seen.add(ts)
            per_day[day].spo2_sum += min(max(pct, 0.0), 100.0)
            per_day[day].spo2_count += 1

    # Materialize sleep seen -> per-day.
    for token, hours in sleep_seen.items():
        day = _date_prefix(token.split("|", 1)[0])
        if day in per_day:
            per_day[day].sleep_hours += hours

    out: List[HealthDay] = []
    for day in days:
        agg = per_day[day]
        resting_avg = (agg.resting_hr_sum / agg.resting_hr_count) if agg.resting_hr_count else None
        hr_avg = (agg.hr_sum / agg.hr_count) if agg.hr_count else None
        spo2_avg = (agg.spo2_sum / agg.spo2_count) if agg.spo2_count else None
        out.append(
            HealthDay(
                date=day,
                sleep_hours=round(agg.sleep_hours, 2),
                resting_hr_avg_bpm=round(resting_avg, 1) if resting_avg is not None else None,
                hr_avg_bpm=round(hr_avg, 1) if hr_avg is not None else None,
                hr_max_bpm=round(agg.hr_max, 1) if agg.hr_count else None,
                spo2_avg_pct=round(spo2_avg, 1) if spo2_avg is not None else None,
            )
        )

    return out, warnings, last_synced_at


def get_device_health_summary(user_id: str, device_id: str, *, start: str, end: str) -> Dict[str, Any]:
    days, warnings, last_synced_at = _aggregate_device(user_id, device_id, start=start, end=end)
    resp = HealthSummaryResponse(
        subject_id=device_id,
        subject_type="device",
        start=start,
        end=end,
        days=days,
        warnings=warnings,
        last_healthkit_sync_at=last_synced_at,
    )
    return resp.model_dump()
