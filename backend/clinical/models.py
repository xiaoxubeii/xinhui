# -*- coding: utf-8 -*-
"""Clinical records — Pydantic models.

Design goals:
- Store clinical records (e.g. CPET report) as structured JSON, keyed by patient_id.
- Keep storage simple (JSON files) for easy local deployment.
- Allow linking one patient to one or more device_id values (for lifestyle aggregation).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Sex(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class ClinicalRecordType(str, Enum):
    cpet_report = "cpet_report"
    lab_result = "lab_result"
    imaging_report = "imaging_report"
    diagnosis = "diagnosis"
    medication = "medication"
    note = "note"


class ClinicalSubjectUpsertRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    name: Optional[str] = Field(None, max_length=128)
    sex: Sex = Sex.unknown
    age: Optional[int] = Field(None, ge=0, le=130)
    height_cm: Optional[float] = Field(None, ge=0, le=300)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    diagnosis: List[str] = Field(default_factory=list)
    linked_device_ids: List[str] = Field(default_factory=list, description="For lifestyle linkage")
    notes: Optional[str] = Field(None, max_length=2000)


class ClinicalSubject(BaseModel):
    patient_id: str
    name: Optional[str] = None
    sex: Sex = Sex.unknown
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    diagnosis: List[str] = Field(default_factory=list)
    linked_device_ids: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class ClinicalRecordCreateRequest(BaseModel):
    patient_id: str = Field(..., min_length=1)
    record_type: ClinicalRecordType
    recorded_at: str = Field(..., description="ISO8601 timestamp for when the record happened")
    title: Optional[str] = Field(None, max_length=256)
    tags: List[str] = Field(default_factory=list)
    source: str = Field("manual", max_length=64)
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured payload (e.g. parsed CPET)")


class ClinicalRecord(BaseModel):
    record_id: str
    patient_id: str
    record_type: ClinicalRecordType
    recorded_at: str
    title: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source: str = "manual"
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ClinicalRecordCreateResponse(BaseModel):
    record_id: str
    saved_at: str


class ClinicalRecordsResponse(BaseModel):
    patient_id: str
    count: int
    records: List[ClinicalRecord]


class ClinicalSubjectsResponse(BaseModel):
    count: int
    subjects: List[ClinicalSubject]

