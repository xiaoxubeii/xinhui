# -*- coding: utf-8 -*-
"""Exercise domain — Pydantic models."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ExerciseDay(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    steps: int = Field(0, ge=0)
    workout_energy_kcal: float = Field(0.0, ge=0)
    workout_count: int = Field(0, ge=0)


class ExerciseSummaryResponse(BaseModel):
    subject_id: str = Field(..., description="device_id or patient_id")
    subject_type: str = Field(..., description="device|patient")
    start: str
    end: str
    days: List[ExerciseDay]
    warnings: List[str] = Field(default_factory=list)
    last_healthkit_sync_at: Optional[str] = None

