# -*- coding: utf-8 -*-
"""Health domain — Pydantic models."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class HealthDay(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    sleep_hours: float = Field(0.0, ge=0)
    resting_hr_avg_bpm: Optional[float] = Field(None, ge=0)
    hr_avg_bpm: Optional[float] = Field(None, ge=0)
    hr_max_bpm: Optional[float] = Field(None, ge=0)
    spo2_avg_pct: Optional[float] = Field(None, ge=0, le=100)


class HealthSummaryResponse(BaseModel):
    subject_id: str = Field(..., description="device_id or patient_id")
    subject_type: str = Field(..., description="device|patient")
    start: str
    end: str
    days: List[HealthDay]
    warnings: List[str] = Field(default_factory=list)
    last_healthkit_sync_at: Optional[str] = None

