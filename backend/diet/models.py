# -*- coding: utf-8 -*-
"""Diet — Pydantic models."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class NutritionTotals(BaseModel):
    calories_kcal: float = Field(0.0, ge=0)
    protein_g: float = Field(0.0, ge=0)
    carbs_g: float = Field(0.0, ge=0)
    fat_g: float = Field(0.0, ge=0)


class FoodItem(BaseModel):
    name: str = Field(..., min_length=1, description="Food name, e.g. 'rice', 'apple'")
    portion: Optional[str] = Field(None, description="Human-readable portion, e.g. '1 bowl'")
    grams: Optional[float] = Field(None, ge=0, description="Estimated grams for the portion")
    calories_kcal: Optional[float] = Field(None, ge=0)
    protein_g: Optional[float] = Field(None, ge=0)
    carbs_g: Optional[float] = Field(None, ge=0)
    fat_g: Optional[float] = Field(None, ge=0)
    confidence: Optional[float] = Field(None, ge=0, le=1)


class DietRecognizeRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    captured_at: str = Field(..., description="ISO8601 timestamp")
    image_mime: str = Field(..., pattern=r"^image/(jpeg|jpg|png|heic)$")
    image_base64: str = Field(..., min_length=16, description="Raw base64 without data-url prefix")
    locale: Optional[str] = Field(None, description="e.g. zh-CN")


class DietRecognizeResponse(BaseModel):
    request_id: str
    items: List[FoodItem] = []
    totals: NutritionTotals = NutritionTotals()
    warnings: List[str] = []
    model: str


class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class DietCreateEntryRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    eaten_at: str = Field(..., description="ISO8601 timestamp")
    meal_type: MealType
    items: List[FoodItem] = Field(default_factory=list)
    notes: Optional[str] = Field(None, max_length=2000)
    source: Optional[str] = Field("vision", max_length=64)
    plan_id: Optional[str] = Field(None, description="关联的营养规划 ID")


class DietCreateEntryResponse(BaseModel):
    entry_id: str
    saved_at: str
    totals: NutritionTotals


class DietEntry(BaseModel):
    entry_id: str
    device_id: str
    created_at: str
    eaten_at: str
    meal_type: MealType
    items: List[FoodItem] = []
    totals: NutritionTotals = NutritionTotals()
    notes: Optional[str] = None
    source: str = "vision"
    warnings: List[str] = []
    plan_id: Optional[str] = None


class DietEntriesResponse(BaseModel):
    device_id: str
    count: int
    entries: List[DietEntry]


class DietDailySummary(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    totals: NutritionTotals
    entry_count: int = Field(0, ge=0)


class DietSummaryResponse(BaseModel):
    device_id: str
    start: str
    end: str
    totals: NutritionTotals
    days: List[DietDailySummary]


class DietVisionRawResult(BaseModel):
    items: List[FoodItem] = []
    totals: Optional[NutritionTotals] = None
    warnings: List[str] = []
    extra: Dict[str, object] = Field(default_factory=dict, description="Reserved for model-specific fields")

    @field_validator("warnings", mode="before")
    @classmethod
    def _coerce_warnings(cls, value: object) -> List[str]:
        """LLM outputs are often inconsistent (e.g., warnings: "..." vs ["..."]).

        Keep the API resilient so the iOS client gets a usable response instead of a 500.
        """
        if value is None:
            return []
        if isinstance(value, str):
            v = value.strip()
            return [v] if v else []
        if isinstance(value, list):
            out: List[str] = []
            for item in value:
                if item is None:
                    continue
                s = str(item).strip()
                if s:
                    out.append(s)
            return out
        # Fallback: stringify unknown shapes (dict/number/etc.)
        s = str(value).strip()
        return [s] if s else []
