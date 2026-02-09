# -*- coding: utf-8 -*-
"""Health domain — API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.security import get_current_user
from ..clinical.storage import get_subject
from .models import HealthDay, HealthSummaryResponse
from .storage import get_device_health_summary

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("/summary/{device_id}", response_model=HealthSummaryResponse, summary="Health daily summary for a device")
def health_summary_device(
    device_id: str,
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    user: dict = Depends(get_current_user),
):
    data = get_device_health_summary(user["id"], device_id, start=start, end=end)
    return HealthSummaryResponse.model_validate(data)


@router.get(
    "/summary/patient/{patient_id}",
    response_model=HealthSummaryResponse,
    summary="Health daily summary for a patient (merged devices)",
)
def health_summary_patient(
    patient_id: str,
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    device: str = Query(default="all", description="all or a specific device_id"),
    merge: str = Query(default="sum", pattern="^(sum|max)$", description="merge strategy across devices"),
    user: dict = Depends(get_current_user),
):
    if patient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    subject = get_subject(patient_id)
    device_ids: list[str] = []
    if subject and subject.linked_device_ids:
        device_ids = list(subject.linked_device_ids)
    if device != "all":
        device_ids = [device]

    # Merge device summaries.
    combined: dict[str, dict] = {}
    last_sync: str | None = None
    warnings: list[str] = []
    if not device_ids:
        warnings.append("No linked devices for patient")
        return HealthSummaryResponse(
            subject_id=patient_id,
            subject_type="patient",
            start=start,
            end=end,
            days=[],
            warnings=warnings,
            last_healthkit_sync_at=None,
        )
    for device_id in device_ids:
        summary = HealthSummaryResponse.model_validate(get_device_health_summary(user["id"], device_id, start=start, end=end))
        warnings.extend(summary.warnings)
        if summary.last_healthkit_sync_at and (not last_sync or summary.last_healthkit_sync_at > last_sync):
            last_sync = summary.last_healthkit_sync_at
        for day in summary.days:
            bucket = combined.setdefault(day.date, {"sleep_hours": [], "resting": [], "hr_avg": [], "hr_max": [], "spo2": []})
            bucket["sleep_hours"].append(day.sleep_hours)
            if day.resting_hr_avg_bpm is not None:
                bucket["resting"].append(day.resting_hr_avg_bpm)
            if day.hr_avg_bpm is not None:
                bucket["hr_avg"].append(day.hr_avg_bpm)
            if day.hr_max_bpm is not None:
                bucket["hr_max"].append(day.hr_max_bpm)
            if day.spo2_avg_pct is not None:
                bucket["spo2"].append(day.spo2_avg_pct)

    merged_days = []
    for day in sorted(combined.keys()):
        b = combined[day]
        if merge == "sum":
            sleep_hours = round(sum(b["sleep_hours"]), 2)
        else:
            sleep_hours = round(max(b["sleep_hours"] or [0.0]), 2)

        # For vitals, max merge is usually safer; keep it simple:
        resting = (sum(b["resting"]) / len(b["resting"])) if b["resting"] else None
        hr_avg = (sum(b["hr_avg"]) / len(b["hr_avg"])) if b["hr_avg"] else None
        hr_max = max(b["hr_max"]) if b["hr_max"] else None
        spo2 = (sum(b["spo2"]) / len(b["spo2"])) if b["spo2"] else None

        merged_days.append(
            HealthDay(
                date=day,
                sleep_hours=sleep_hours,
                resting_hr_avg_bpm=round(resting, 1) if resting is not None else None,
                hr_avg_bpm=round(hr_avg, 1) if hr_avg is not None else None,
                hr_max_bpm=round(hr_max, 1) if hr_max is not None else None,
                spo2_avg_pct=round(spo2, 1) if spo2 is not None else None,
            )
        )

    resp = HealthSummaryResponse(
        subject_id=patient_id,
        subject_type="patient",
        start=start,
        end=end,
        days=merged_days,
        warnings=warnings,
        last_healthkit_sync_at=last_sync,
    )
    return resp
