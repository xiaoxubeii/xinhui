# -*- coding: utf-8 -*-
"""Diet — JSON file storage (no image retention)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import DietDailySummary, DietEntry, NutritionTotals

from ..config import settings


def _data_root_for(user_id: str) -> Path:
    return settings.data_root / "users" / user_id / "diet"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def compute_totals(items: List[Dict[str, Any]]) -> NutritionTotals:
    calories = 0.0
    protein = 0.0
    carbs = 0.0
    fat = 0.0
    for item in items:
        calories += float(item.get("calories_kcal") or 0.0)
        protein += float(item.get("protein_g") or 0.0)
        carbs += float(item.get("carbs_g") or 0.0)
        fat += float(item.get("fat_g") or 0.0)
    return NutritionTotals(
        calories_kcal=round(calories, 1),
        protein_g=round(protein, 1),
        carbs_g=round(carbs, 1),
        fat_g=round(fat, 1),
    )


def save_entry(
    user_id: str,
    entry: DietEntry,
    data_root: Path | None = None,
) -> str:
    root = data_root or _data_root_for(user_id)
    device_dir = root / entry.device_id
    _ensure_dir(device_dir)
    fp = device_dir / f"{entry.entry_id}.json"
    fp.write_text(entry.model_dump_json(ensure_ascii=False, indent=2), encoding="utf-8")
    return entry.entry_id


def create_entry_record(
    *,
    device_id: str,
    eaten_at: str,
    meal_type: str,
    items: List[Dict[str, Any]],
    notes: Optional[str],
    source: str,
    warnings: List[str],
) -> DietEntry:
    now = datetime.utcnow().isoformat() + "Z"
    entry_id = str(uuid4())
    totals = compute_totals(items)
    return DietEntry(
        entry_id=entry_id,
        device_id=device_id,
        created_at=now,
        eaten_at=eaten_at,
        meal_type=meal_type,
        items=items,
        totals=totals,
        notes=notes,
        source=source,
        warnings=warnings,
    )


def _iter_device_entries(device_id: str, data_root: Path) -> List[DietEntry]:
    device_dir = data_root / device_id
    if not device_dir.exists():
        return []

    entries: List[DietEntry] = []
    for fp in sorted(device_dir.glob("*.json"), reverse=True):
        try:
            raw = json.loads(fp.read_text(encoding="utf-8"))
            entries.append(DietEntry.model_validate(raw))
        except Exception:
            continue
    return entries


def _date_prefix(iso8601: str) -> str:
    # Most ISO8601 strings start with YYYY-MM-DD; keep it robust without strict parsing.
    return (iso8601 or "")[:10]


def get_device_entries(
    user_id: str,
    device_id: str,
    *,
    start: Optional[str] = None,
    end: Optional[str] = None,
    data_root: Path | None = None,
) -> List[DietEntry]:
    root = data_root or _data_root_for(user_id)
    entries = _iter_device_entries(device_id, root)
    if not start and not end:
        return entries

    start_date = start or "0000-01-01"
    end_date = end or "9999-12-31"

    def in_range(entry: DietEntry) -> bool:
        d = _date_prefix(entry.eaten_at)
        return start_date <= d <= end_date

    return [e for e in entries if in_range(e)]


def get_device_summary(
    user_id: str,
    device_id: str,
    *,
    start: str,
    end: str,
    data_root: Path | None = None,
) -> Dict[str, Any]:
    root = data_root or _data_root_for(user_id)
    entries = get_device_entries(user_id, device_id, start=start, end=end, data_root=root)

    per_day: Dict[str, Dict[str, Any]] = {}
    totals = NutritionTotals()

    for entry in entries:
        day = _date_prefix(entry.eaten_at)
        if day not in per_day:
            per_day[day] = {"totals": NutritionTotals(), "entry_count": 0}
        per_day[day]["entry_count"] += 1
        day_totals: NutritionTotals = per_day[day]["totals"]
        day_totals.calories_kcal += entry.totals.calories_kcal
        day_totals.protein_g += entry.totals.protein_g
        day_totals.carbs_g += entry.totals.carbs_g
        day_totals.fat_g += entry.totals.fat_g

        totals.calories_kcal += entry.totals.calories_kcal
        totals.protein_g += entry.totals.protein_g
        totals.carbs_g += entry.totals.carbs_g
        totals.fat_g += entry.totals.fat_g

    days: List[DietDailySummary] = []
    for day in sorted(per_day.keys()):
        day_totals = per_day[day]["totals"]
        days.append(
            DietDailySummary(
                date=day,
                totals=NutritionTotals(
                    calories_kcal=round(day_totals.calories_kcal, 1),
                    protein_g=round(day_totals.protein_g, 1),
                    carbs_g=round(day_totals.carbs_g, 1),
                    fat_g=round(day_totals.fat_g, 1),
                ),
                entry_count=per_day[day]["entry_count"],
            )
        )

    return {
        "device_id": device_id,
        "start": start,
        "end": end,
        "totals": NutritionTotals(
            calories_kcal=round(totals.calories_kcal, 1),
            protein_g=round(totals.protein_g, 1),
            carbs_g=round(totals.carbs_g, 1),
            fat_g=round(totals.fat_g, 1),
        ),
        "days": days,
    }
