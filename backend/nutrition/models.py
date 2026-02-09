# -*- coding: utf-8 -*-
"""Nutrition domain — Pydantic models."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class NutritionTotals(BaseModel):
    calories_kcal: float = Field(0.0, ge=0)
    protein_g: float = Field(0.0, ge=0)
    carbs_g: float = Field(0.0, ge=0)
    fat_g: float = Field(0.0, ge=0)


class NutritionDay(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    totals: NutritionTotals
    entry_count: int = Field(0, ge=0)


class NutritionSummaryResponse(BaseModel):
    subject_id: str = Field(..., description="device_id or patient_id")
    subject_type: str = Field(..., description="device|patient")
    start: str
    end: str
    totals: NutritionTotals
    days: List[NutritionDay]
    warnings: List[str] = Field(default_factory=list)
    last_diet_entry_at: Optional[str] = None

