# -*- coding: utf-8 -*-
"""API keys — API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth.security import get_current_user
from .models import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyListItem, ApiKeyListResponse
from .storage import create_api_key, list_api_keys, revoke_api_key

router = APIRouter(prefix="/api/api-keys", tags=["API Keys"])


@router.post("", response_model=ApiKeyCreateResponse, summary="Create an API key")
def create_key(request: ApiKeyCreateRequest, user: dict = Depends(get_current_user)):
    row, full_key = create_api_key(user_id=user["id"], name=request.name)
    return ApiKeyCreateResponse(
        id=row["id"],
        name=row.get("name"),
        prefix=row["prefix"],
        api_key=full_key,
        created_at=row["created_at"],
    )


@router.get("", response_model=ApiKeyListResponse, summary="List API keys")
def list_keys(user: dict = Depends(get_current_user)):
    rows = list_api_keys(user_id=user["id"])
    items = [
        ApiKeyListItem(
            id=r["id"],
            name=r.get("name"),
            prefix=r["prefix"],
            created_at=r["created_at"],
            last_used_at=r.get("last_used_at"),
            revoked_at=r.get("revoked_at"),
        )
        for r in rows
    ]
    return ApiKeyListResponse(count=len(items), items=items)


@router.delete("/{key_id}", summary="Revoke an API key")
def revoke_key(key_id: str, user: dict = Depends(get_current_user)):
    ok = revoke_api_key(user_id=user["id"], key_id=key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "ok", "key_id": key_id}

