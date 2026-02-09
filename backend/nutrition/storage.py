# -*- coding: utf-8 -*-
"""Nutrition domain aggregation (wraps diet storage, plus patient-level merge)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..clinical.storage import get_subject
from ..diet.storage import get_device_entries as _get_device_entries
from ..diet.storage import get_device_summary as _get_device_summary
from .models import NutritionDay, NutritionSummaryResponse, NutritionTotals


def _totals_from_obj(obj: Any) -> NutritionTotals:
    if isinstance(obj, NutritionTotals):
        return obj
    if hasattr(obj, "model_dump"):
        data = obj.model_dump()
    elif isinstance(obj, dict):
        data = obj
    else:
        data = {}
    return NutritionTotals(
        calories_kcal=float(data.get("calories_kcal") or 0.0),
        protein_g=float(data.get("protein_g") or 0.0),
        carbs_g=float(data.get("carbs_g") or 0.0),
        fat_g=float(data.get("fat_g") or 0.0),
    )


def get_device_nutrition_summary(user_id: str, device_id: str, *, start: str, end: str) -> Dict[str, Any]:
    data = _get_device_summary(user_id, device_id, start=start, end=end)
    totals = _totals_from_obj(data.get("totals"))
    days = [
        NutritionDay(date=d.date, totals=_totals_from_obj(d.totals), entry_count=d.entry_count)  # type: ignore[attr-defined]
        for d in data.get("days", [])
    ]

    # Compute last entry time within range.
    last_entry_at: Optional[str] = None
    try:
        entries = _get_device_entries(user_id, device_id, start=start, end=end)
        for e in entries:
            eaten_at = getattr(e, "eaten_at", None)
            if eaten_at and (not last_entry_at or eaten_at > last_entry_at):
                last_entry_at = eaten_at
    except Exception:
        last_entry_at = None

    resp = NutritionSummaryResponse(
        subject_id=device_id,
        subject_type="device",
        start=start,
        end=end,
        totals=totals,
        days=days,
        warnings=[],
        last_diet_entry_at=last_entry_at,
    )
    return resp.model_dump()


def get_patient_nutrition_summary(
    user_id: str,
    patient_id: str,
    *,
    start: str,
    end: str,
    device: str = "all",
    merge: str = "sum",
) -> Dict[str, Any]:
    subject = get_subject(patient_id)
    device_ids: List[str] = []
    if subject and subject.linked_device_ids:
        device_ids = list(subject.linked_device_ids)
    if device != "all":
        device_ids = [device]

    per_day: Dict[str, NutritionDay] = {}
    totals = NutritionTotals()
    warnings: List[str] = []
    last_entry_at: Optional[str] = None

    if not device_ids:
        warnings.append("No linked devices for patient")
    else:
        for device_id in device_ids:
            s = NutritionSummaryResponse.model_validate(get_device_nutrition_summary(user_id, device_id, start=start, end=end))
            if s.last_diet_entry_at and (not last_entry_at or s.last_diet_entry_at > last_entry_at):
                last_entry_at = s.last_diet_entry_at
            for d in s.days:
                bucket = per_day.setdefault(d.date, NutritionDay(date=d.date, totals=NutritionTotals(), entry_count=0))
                if merge == "max":
                    bucket.entry_count = max(bucket.entry_count, d.entry_count)
                    bucket.totals.calories_kcal = max(bucket.totals.calories_kcal, d.totals.calories_kcal)
                    bucket.totals.protein_g = max(bucket.totals.protein_g, d.totals.protein_g)
                    bucket.totals.carbs_g = max(bucket.totals.carbs_g, d.totals.carbs_g)
                    bucket.totals.fat_g = max(bucket.totals.fat_g, d.totals.fat_g)
                else:
                    bucket.entry_count += d.entry_count
                    bucket.totals.calories_kcal += d.totals.calories_kcal
                    bucket.totals.protein_g += d.totals.protein_g
                    bucket.totals.carbs_g += d.totals.carbs_g
                    bucket.totals.fat_g += d.totals.fat_g

    days = [per_day[k] for k in sorted(per_day.keys())]
    # Totals should always be derived from merged day buckets (sum across days).
    # - merge=sum: sums device totals per day, then sums across days
    # - merge=max: takes max across devices per day, then sums across days
    for d in days:
        totals.calories_kcal += d.totals.calories_kcal
        totals.protein_g += d.totals.protein_g
        totals.carbs_g += d.totals.carbs_g
        totals.fat_g += d.totals.fat_g

    totals.calories_kcal = round(totals.calories_kcal, 1)
    totals.protein_g = round(totals.protein_g, 1)
    totals.carbs_g = round(totals.carbs_g, 1)
    totals.fat_g = round(totals.fat_g, 1)

    resp = NutritionSummaryResponse(
        subject_id=patient_id,
        subject_type="patient",
        start=start,
        end=end,
        totals=totals,
        days=days,
        warnings=warnings,
        last_diet_entry_at=last_entry_at,
    )
    return resp.model_dump()
