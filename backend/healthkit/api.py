# -*- coding: utf-8 -*-
"""HealthKit 数据同步 — API 端点"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth.security import get_current_user
from ..clinical.models import ClinicalSubjectUpsertRequest
from ..clinical.storage import get_subject, upsert_subject
from .models import HealthSyncRequest, HealthSyncResponse
from .storage import get_device_summary, get_device_syncs, save_sync_data

router = APIRouter(prefix="/api/healthkit", tags=["HealthKit"])


@router.post("/sync", response_model=HealthSyncResponse, summary="接收并存储 HealthKit 健康数据")
def sync_health_data(request: HealthSyncRequest, user: dict = Depends(get_current_user)):
    """iOS 客户端调用此端点上传 HealthKit 数据。"""
    payload = request.model_dump()

    received_counts = {
        "daily_steps": len(request.daily_steps),
        "heart_rate_samples": len(request.heart_rate_samples),
        "resting_heart_rates": len(request.resting_heart_rates),
        "spo2_readings": len(request.spo2_readings),
        "sleep_sessions": len(request.sleep_sessions),
        "workouts": len(request.workouts),
    }

    total = sum(received_counts.values())
    if total == 0:
        return HealthSyncResponse(
            status="ok",
            message="No data received",
            received_counts=received_counts,
            sync_id="",
        )

    try:
        sync_id = save_sync_data(user["id"], request.device_id, payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save sync data: {exc}") from exc

    # Ensure the device_id is linked to the current user (personal-mode patient_id=user.id).
    try:
        subject = get_subject(user["id"])
        linked = list(subject.linked_device_ids) if subject else []
        if request.device_id not in linked:
            linked.append(request.device_id)
            upsert_subject(ClinicalSubjectUpsertRequest(patient_id=user["id"], linked_device_ids=linked))
    except Exception:
        pass

    return HealthSyncResponse(
        status="ok",
        message=f"Received {total} records",
        received_counts=received_counts,
        sync_id=sync_id,
    )


@router.get("/history/{device_id}", summary="查询设备的同步历史")
def get_sync_history(device_id: str, user: dict = Depends(get_current_user)):
    """返回指定设备的所有同步记录摘要。"""
    syncs = get_device_syncs(user["id"], device_id)
    return {"device_id": device_id, "syncs": syncs, "count": len(syncs)}


@router.get("/summary/{device_id}", summary="获取设备的数据摘要")
def get_device_data_summary(device_id: str, user: dict = Depends(get_current_user)):
    """汇总指定设备的所有已同步数据。"""
    return get_device_summary(user["id"], device_id)
