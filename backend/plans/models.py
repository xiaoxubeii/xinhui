# -*- coding: utf-8 -*-
"""Plan models for API payloads."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


PlanType = Literal["exercise", "nutrition"]


class PlanDraftRequest(BaseModel):
    session_id: str
    patient_id: str
    plan_type: PlanType


class PlanDraftResponse(BaseModel):
    draft_id: str
    plan_type: PlanType
    summary: str
    payload: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
    status: str = "draft"


class PlanConfirmRequest(BaseModel):
    draft_id: str


class PlanConfirmResponse(BaseModel):
    status: str
    plan_id: str
    confirmed_at: Optional[str] = None


class PlanFetchResponse(BaseModel):
    plan_id: str
    plan_type: PlanType
    summary: str
    payload: Dict[str, Any]
    confirmed_at: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class PlanListItem(BaseModel):
    plan_id: str
    plan_type: PlanType
    summary: str
    payload: Dict[str, Any]
    status: str
    confirmed_at: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class PlanListResponse(BaseModel):
    items: List[PlanListItem]


class ExercisePlanResponse(BaseModel):
    plan_id: str
    title: Optional[str] = None
    summary: str
    sessions: List[Dict[str, Any]] = Field(default_factory=list)
    goals: Optional[Dict[str, Any]] = None
    generated_at: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class NutritionPlanResponse(BaseModel):
    plan_id: str
    title: Optional[str] = None
    summary: str
    macros: Optional[Dict[str, Any]] = None
    meals: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: Optional[Dict[str, Any]] = None
    generated_at: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
