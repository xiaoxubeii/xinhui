# -*- coding: utf-8 -*-
"""Lifestyle aggregation — API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.security import get_current_user
from .models import LifestyleSummaryResponse
from .storage import get_device_lifestyle_summary, get_patient_lifestyle_summary

router = APIRouter(prefix="/api/lifestyle", tags=["Lifestyle"])


@router.get("/summary/{device_id}", response_model=LifestyleSummaryResponse, summary="Lifestyle daily summary")
def lifestyle_summary(
    device_id: str,
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    user: dict = Depends(get_current_user),
):
    data = get_device_lifestyle_summary(user["id"], device_id, start=start, end=end)
    return LifestyleSummaryResponse.model_validate(data)


@router.get(
    "/summary/patient/{patient_id}",
    response_model=LifestyleSummaryResponse,
    summary="Lifestyle daily summary for a patient (merged devices)",
)
def lifestyle_summary_patient(
    patient_id: str,
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    device: str = Query(default="all", description="all or a specific device_id"),
    merge: str = Query(default="sum", pattern="^(sum|max)$", description="merge strategy across devices"),
    user: dict = Depends(get_current_user),
):
    if patient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    data = get_patient_lifestyle_summary(user["id"], patient_id, start=start, end=end, device=device, merge=merge)
    return LifestyleSummaryResponse.model_validate(data)
