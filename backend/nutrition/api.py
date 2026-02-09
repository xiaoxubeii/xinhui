# -*- coding: utf-8 -*-
"""Nutrition domain — API endpoints (alias for diet)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.security import get_current_user
from .models import NutritionSummaryResponse
from .storage import get_device_nutrition_summary, get_patient_nutrition_summary

router = APIRouter(prefix="/api/nutrition", tags=["Nutrition"])


@router.get("/summary/{device_id}", response_model=NutritionSummaryResponse, summary="Nutrition daily summary for a device")
def nutrition_summary_device(
    device_id: str,
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    user: dict = Depends(get_current_user),
):
    data = get_device_nutrition_summary(user["id"], device_id, start=start, end=end)
    return NutritionSummaryResponse.model_validate(data)


@router.get(
    "/summary/patient/{patient_id}",
    response_model=NutritionSummaryResponse,
    summary="Nutrition daily summary for a patient (merged devices)",
)
def nutrition_summary_patient(
    patient_id: str,
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    device: str = Query(default="all", description="all or a specific device_id"),
    merge: str = Query(default="sum", pattern="^(sum|max)$", description="merge strategy across devices"),
    user: dict = Depends(get_current_user),
):
    if patient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    data = get_patient_nutrition_summary(user["id"], patient_id, start=start, end=end, device=device, merge=merge)
    return NutritionSummaryResponse.model_validate(data)
