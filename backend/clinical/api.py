# -*- coding: utf-8 -*-
"""Clinical records — API endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.security import get_current_user
from .models import (
    ClinicalRecordCreateRequest,
    ClinicalRecordCreateResponse,
    ClinicalRecordType,
    ClinicalRecordsResponse,
    ClinicalSubject,
    ClinicalSubjectUpsertRequest,
    ClinicalSubjectsResponse,
)
from .storage import (
    create_record,
    delete_record,
    get_record,
    get_subject,
    latest_record,
    list_records,
    list_subjects,
    upsert_subject,
)

router = APIRouter(prefix="/api/clinical", tags=["Clinical"])


@router.post("/subjects", response_model=ClinicalSubject, summary="Upsert a clinical subject (patient)")
def upsert_subject_api(request: ClinicalSubjectUpsertRequest, user: dict = Depends(get_current_user)):
    if request.patient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return upsert_subject(request)


@router.get("/subjects/{patient_id}", response_model=ClinicalSubject, summary="Get a clinical subject")
def get_subject_api(patient_id: str, user: dict = Depends(get_current_user)):
    if patient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    subject = get_subject(patient_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router.get("/subjects", response_model=ClinicalSubjectsResponse, summary="List clinical subjects")
def list_subjects_api(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    # Personal-mode: only expose current user.
    subject = get_subject(user["id"])
    subjects = [subject] if subject else []
    return ClinicalSubjectsResponse(count=len(subjects), subjects=subjects)


@router.post("/records", response_model=ClinicalRecordCreateResponse, summary="Create a clinical record")
def create_record_api(request: ClinicalRecordCreateRequest, user: dict = Depends(get_current_user)):
    if request.patient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    # Make sure a subject exists (minimum info) to keep data discoverable.
    if not get_subject(request.patient_id):
        upsert_subject(ClinicalSubjectUpsertRequest(patient_id=request.patient_id))

    record = create_record(request)
    return ClinicalRecordCreateResponse(record_id=record.record_id, saved_at=record.created_at)


@router.get("/records/{patient_id}", response_model=ClinicalRecordsResponse, summary="List clinical records")
def list_records_api(
    patient_id: str,
    record_type: ClinicalRecordType | None = Query(default=None),
    start: str | None = Query(default=None, description="YYYY-MM-DD"),
    end: str | None = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    if patient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    items = list_records(
        patient_id,
        record_type=record_type,
        start=start,
        end=end,
        limit=limit,
        offset=offset,
    )
    return ClinicalRecordsResponse(patient_id=patient_id, count=len(items), records=items)


@router.get("/records/{patient_id}/{record_id}", summary="Get a clinical record")
def get_record_api(patient_id: str, record_id: str, user: dict = Depends(get_current_user)):
    if patient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    record = get_record(patient_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.delete("/records/{patient_id}/{record_id}", summary="Delete a clinical record")
def delete_record_api(patient_id: str, record_id: str, user: dict = Depends(get_current_user)):
    if patient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    ok = delete_record(patient_id, record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "ok", "record_id": record_id}


@router.get("/context/{patient_id}", summary="Clinical context for agents (subject + latest CPET + optional lifestyle)")
def get_clinical_context(
    patient_id: str,
    days: int = Query(default=7, ge=1, le=30),
    device: str = Query(default="all", description="all or a specific device_id"),
    merge: str = Query(default="sum", pattern="^(sum|max)$", description="merge strategy across devices"),
    user: dict = Depends(get_current_user),
):
    if patient_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    subject = get_subject(patient_id)
    latest_cpet = latest_record(patient_id, ClinicalRecordType.cpet_report)

    lifestyle = None
    linked_device_ids = subject.linked_device_ids if subject else []
    try:
        from ..lifestyle.storage import get_patient_lifestyle_summary

        end = date.today()
        start = end - timedelta(days=days - 1)
        lifestyle = get_patient_lifestyle_summary(
            user["id"],
            patient_id,
            start=start.isoformat(),
            end=end.isoformat(),
            device=device,
            merge=merge,
        )
    except Exception:
        lifestyle = None

    return {
        "patient": subject.model_dump() if subject else {"patient_id": patient_id},
        "latest_cpet": latest_cpet.model_dump() if latest_cpet else None,
        "linked_device_ids": linked_device_ids,
        "device_filter": device,
        "merge_strategy": merge,
        "lifestyle": lifestyle,
    }
