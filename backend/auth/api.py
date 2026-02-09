# -*- coding: utf-8 -*-
"""Auth — API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from ..clinical.models import ClinicalSubjectUpsertRequest
from ..clinical.storage import upsert_subject
from ..config import settings
from .models import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from .security import TOKEN_COOKIE_NAME, create_access_token, get_current_user, hash_password, verify_password
from .storage import create_user, get_user_by_email

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _user_public(row: dict) -> UserPublic:
    return UserPublic(id=row["id"], email=row["email"], created_at=row["created_at"])


def _set_auth_cookie(resp: Response, token: str) -> None:
    max_age = int(settings.token_ttl_days) * 24 * 60 * 60
    resp.set_cookie(
        TOKEN_COOKIE_NAME,
        token,
        httponly=True,
        secure=bool(settings.cookie_secure),
        samesite="lax",
        max_age=max_age,
        path="/",
    )


@router.post("/register", response_model=AuthResponse, summary="Register a new user")
def register(request: RegisterRequest, response: Response):
    existing = get_user_by_email(request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    password_hash = hash_password(request.password)
    user = create_user(email=str(request.email), password_hash=password_hash)

    # Personal-mode: create a clinical subject keyed by user.id.
    try:
        upsert_subject(ClinicalSubjectUpsertRequest(patient_id=user["id"]))
    except Exception:
        # Subject is an optional convenience; auth must still succeed.
        pass

    token = create_access_token(user_id=user["id"], email=user["email"])
    _set_auth_cookie(response, token)
    return AuthResponse(user=_user_public(user), token=token)


@router.post("/login", response_model=AuthResponse, summary="Login")
def login(request: LoginRequest, response: Response):
    user = get_user_by_email(request.email)
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=user["id"], email=user["email"])
    _set_auth_cookie(response, token)
    return AuthResponse(user=_user_public(user), token=token)


@router.post("/logout", summary="Logout")
def logout(response: Response):
    response.delete_cookie(TOKEN_COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=UserPublic, summary="Get current user")
def me(user: dict = Depends(get_current_user)):
    return _user_public(user)
