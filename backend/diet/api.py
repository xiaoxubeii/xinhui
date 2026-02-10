# -*- coding: utf-8 -*-
"""Diet — API endpoints."""

from __future__ import annotations

import base64
import os
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.security import get_current_user
from .models import (
    DietCreateEntryRequest,
    DietCreateEntryResponse,
    DietEntriesResponse,
    DietRecognizeRequest,
    DietRecognizeResponse,
    DietSummaryResponse,
)
from .storage import create_entry_record, get_device_entries, get_device_summary, save_entry
from .vision import recognize_food

router = APIRouter(prefix="/api/diet", tags=["Diet"])


def _decode_image_or_400(image_base64: str, max_bytes: int) -> bytes:
    try:
        data = base64.b64decode(image_base64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {exc}") from exc
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Image too large: {len(data)} bytes > {max_bytes}")
    return data


@router.post("/recognize", response_model=DietRecognizeResponse, summary="Food photo recognition (no storage)")
def recognize(request: DietRecognizeRequest, user: dict = Depends(get_current_user)):  # noqa: ARG001
    max_bytes = int(os.environ.get("DIET_MAX_IMAGE_BYTES") or "1500000")
    image_bytes = _decode_image_or_400(request.image_base64, max_bytes=max_bytes)

    request_id = str(uuid4())
    try:
        vision_result, model_name = recognize_food(
            image_bytes=image_bytes,
            image_mime=request.image_mime,
            locale=request.locale,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"Vision config/output error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vision model call failed: {exc}") from exc

    return DietRecognizeResponse(
        request_id=request_id,
        items=vision_result.items,
        totals=vision_result.totals,
        warnings=vision_result.warnings,
        model=model_name,
    )


@router.post("/entries", response_model=DietCreateEntryResponse, summary="Create a diet entry")
def create_entry(request: DietCreateEntryRequest, user: dict = Depends(get_current_user)):
    entry = create_entry_record(
        device_id=request.device_id,
        eaten_at=request.eaten_at,
        meal_type=request.meal_type.value,
        items=[i.model_dump() for i in request.items],
        notes=request.notes,
        source=request.source or "vision",
        warnings=[],
        plan_id=request.plan_id,
    )
    try:
        save_entry(user["id"], entry)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save entry: {exc}") from exc

    return DietCreateEntryResponse(
        entry_id=entry.entry_id,
        saved_at=datetime.utcnow().isoformat() + "Z",
        totals=entry.totals,
    )


@router.get("/entries/{device_id}", response_model=DietEntriesResponse, summary="List diet entries")
def list_entries(
    device_id: str,
    start: str | None = Query(default=None, description="YYYY-MM-DD"),
    end: str | None = Query(default=None, description="YYYY-MM-DD"),
    plan_id: str | None = Query(default=None, description="Filter by plan_id"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    entries = get_device_entries(user["id"], device_id, start=start, end=end, plan_id=plan_id)
    sliced = entries[offset : offset + limit]
    return DietEntriesResponse(device_id=device_id, count=len(entries), entries=sliced)


@router.get("/summary/{device_id}", response_model=DietSummaryResponse, summary="Daily summary for a device")
def summary(
    device_id: str,
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    plan_id: str | None = Query(default=None, description="Filter by plan_id"),
    user: dict = Depends(get_current_user),
):
    data = get_device_summary(user["id"], device_id, start=start, end=end, plan_id=plan_id)
    return DietSummaryResponse(
        device_id=device_id,
        start=data["start"],
        end=data["end"],
        totals=data["totals"],
        days=data["days"],
    )
