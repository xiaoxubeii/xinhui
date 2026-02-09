# -*- coding: utf-8 -*-
"""Lifestyle — Pydantic models."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class LifestyleDay(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    steps: int = Field(0, ge=0)
    workout_energy_kcal: float = Field(0.0, ge=0)
    workout_count: int = Field(0, ge=0)
    sleep_hours: float = Field(0.0, ge=0)
    diet_intake_kcal: float = Field(0.0, ge=0)
    diet_entry_count: int = Field(0, ge=0)
    net_kcal: float = Field(0.0, description="diet_intake_kcal - workout_energy_kcal")


class LifestyleTotals(BaseModel):
    steps: int = Field(0, ge=0)
    workout_energy_kcal: float = Field(0.0, ge=0)
    diet_intake_kcal: float = Field(0.0, ge=0)
    net_kcal: float = Field(0.0)
    sleep_hours: float = Field(0.0, ge=0)
    workout_count: int = Field(0, ge=0)
    diet_entry_count: int = Field(0, ge=0)


class LifestyleSummaryResponse(BaseModel):
    device_id: str
    start: str
    end: str
    days: List[LifestyleDay]
    totals: LifestyleTotals
    warnings: List[str] = Field(default_factory=list)
    last_healthkit_sync_at: Optional[str] = None
    last_diet_entry_at: Optional[str] = None

