# -*- coding: utf-8 -*-
"""Plan endpoints (exercise/nutrition)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.security import get_current_user
from .generator import generate_plan_draft
from .models import (
    PlanConfirmRequest,
    PlanConfirmResponse,
    PlanDraftRequest,
    PlanDraftResponse,
    PlanFetchResponse,
    ExercisePlanResponse,
    NutritionPlanResponse,
    PlanListItem,
    PlanListResponse,
)
from .storage import confirm_plan, create_plan_draft, get_latest_confirmed_plan, list_plans_by_session

router = APIRouter(prefix="/api/plans", tags=["Plans"])


@router.post("/draft", response_model=PlanDraftResponse, summary="Generate a plan draft via agent")
def create_plan_draft_api(
    request: PlanDraftRequest,
    user: dict = Depends(get_current_user),
):
    generated = generate_plan_draft(
        user_id=user["id"],
        patient_id=request.patient_id,
        session_id=request.session_id,
        plan_type=request.plan_type,
    )

    draft = create_plan_draft(
        user_id=user["id"],
        patient_id=request.patient_id,
        plan_type=request.plan_type,
        payload=generated["payload"],
        summary=generated["summary"],
        source_session_id=request.session_id,
        source_artifact_ids=[a.get("id") for a in generated.get("context", {}).get("artifacts", [])],
    )

    return PlanDraftResponse(
        draft_id=draft["plan_id"],
        plan_type=request.plan_type,
        summary=draft["summary"],
        payload=draft["payload"],
        warnings=generated.get("warnings") or [],
        status=draft["status"],
    )


@router.post("/confirm", response_model=PlanConfirmResponse, summary="Confirm a plan draft")
def confirm_plan_api(
    request: PlanConfirmRequest,
    user: dict = Depends(get_current_user),
):
    plan = confirm_plan(user_id=user["id"], draft_id=request.draft_id)
    return PlanConfirmResponse(status=plan["status"], plan_id=plan["plan_id"], confirmed_at=plan.get("confirmed_at"))


@router.get("/exercise/{patient_id}", response_model=ExercisePlanResponse, summary="Get latest confirmed exercise plan")
def get_exercise_plan(
    patient_id: str,
    date: str | None = Query(default=None, description="YYYY-MM-DD"),
    user: dict = Depends(get_current_user),
):
    plan = get_latest_confirmed_plan(
        user_id=user["id"],
        patient_id=patient_id,
        plan_type="exercise",
        date=date,
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    payload = plan.get("payload") or {}
    return ExercisePlanResponse(
        plan_id=plan.get("plan_id"),
        title=payload.get("title"),
        summary=payload.get("summary") or plan.get("summary") or "",
        sessions=payload.get("sessions") or [],
        goals=payload.get("goals"),
        generated_at=plan.get("confirmed_at"),
        valid_from=payload.get("valid_from") or plan.get("valid_from"),
        valid_to=payload.get("valid_to") or plan.get("valid_to"),
    )


@router.get("/nutrition/{patient_id}", response_model=NutritionPlanResponse, summary="Get latest confirmed nutrition plan")
def get_nutrition_plan(
    patient_id: str,
    date: str | None = Query(default=None, description="YYYY-MM-DD"),
    user: dict = Depends(get_current_user),
):
    plan = get_latest_confirmed_plan(
        user_id=user["id"],
        patient_id=patient_id,
        plan_type="nutrition",
        date=date,
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    payload = plan.get("payload") or {}
    return NutritionPlanResponse(
        plan_id=plan.get("plan_id"),
        title=payload.get("title"),
        summary=payload.get("summary") or plan.get("summary") or "",
        macros=payload.get("macros"),
        meals=payload.get("meals") or [],
        constraints=payload.get("constraints"),
        generated_at=plan.get("confirmed_at"),
        valid_from=payload.get("valid_from") or plan.get("valid_from"),
        valid_to=payload.get("valid_to") or plan.get("valid_to"),
    )


@router.get("/session/{session_id}", response_model=PlanListResponse, summary="List plans by session")
def list_session_plans(
    session_id: str,
    status: str | None = Query(default="draft", description="Filter by status"),
    plan_type: str | None = Query(default=None, description="exercise | nutrition"),
    user: dict = Depends(get_current_user),
):
    items = list_plans_by_session(
        user_id=user["id"],
        session_id=session_id,
        status=status or None,
        plan_type=plan_type or None,
    )
    return PlanListResponse(items=[PlanListItem(**item) for item in items])
