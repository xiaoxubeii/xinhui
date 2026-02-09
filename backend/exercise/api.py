# -*- coding: utf-8 -*-
"""Exercise domain — API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.security import get_current_user
from ..clinical.storage import get_subject
from .models import ExerciseDay, ExerciseSummaryResponse
from .storage import get_device_exercise_summary

router = APIRouter(prefix="/api/exercise", tags=["Exercise"])


@router.get("/summary/{device_id}", response_model=ExerciseSummaryResponse, summary="Exercise daily summary for a device")
def exercise_summary_device(
    device_id: str,
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    user: dict = Depends(get_current_user),
):
    data = get_device_exercise_summary(user["id"], device_id, start=start, end=end)
    return ExerciseSummaryResponse.model_validate(data)


@router.get(
    "/summary/patient/{patient_id}",
    response_model=ExerciseSummaryResponse,
    summary="Exercise daily summary for a patient (merged devices)",
)
def exercise_summary_patient(
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

    combined: dict[str, dict] = {}
    last_sync: str | None = None
    warnings: list[str] = []
    if not device_ids:
        warnings.append("No linked devices for patient")
        return ExerciseSummaryResponse(
            subject_id=patient_id,
            subject_type="patient",
            start=start,
            end=end,
            days=[],
            warnings=warnings,
            last_healthkit_sync_at=None,
        )
    for device_id in device_ids:
        summary = ExerciseSummaryResponse.model_validate(get_device_exercise_summary(user["id"], device_id, start=start, end=end))
        warnings.extend(summary.warnings)
        if summary.last_healthkit_sync_at and (not last_sync or summary.last_healthkit_sync_at > last_sync):
            last_sync = summary.last_healthkit_sync_at
        for day in summary.days:
            bucket = combined.setdefault(day.date, {"steps": [], "workout_energy_kcal": [], "workout_count": []})
            bucket["steps"].append(day.steps)
            bucket["workout_energy_kcal"].append(day.workout_energy_kcal)
            bucket["workout_count"].append(day.workout_count)

    merged_days: list[ExerciseDay] = []
    for day in sorted(combined.keys()):
        b = combined[day]
        if merge == "sum":
            steps = int(sum(b["steps"]))
            kcal = float(sum(b["workout_energy_kcal"]))
            count = int(sum(b["workout_count"]))
        else:
            steps = int(max(b["steps"] or [0]))
            kcal = float(max(b["workout_energy_kcal"] or [0.0]))
            count = int(max(b["workout_count"] or [0]))
        merged_days.append(
            ExerciseDay(
                date=day,
                steps=steps,
                workout_energy_kcal=round(kcal, 1),
                workout_count=count,
            )
        )

    return ExerciseSummaryResponse(
        subject_id=patient_id,
        subject_type="patient",
        start=start,
        end=end,
        days=merged_days,
        warnings=warnings,
        last_healthkit_sync_at=last_sync,
    )
