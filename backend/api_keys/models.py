# -*- coding: utf-8 -*-
"""API keys — models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=64)


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: Optional[str] = None
    prefix: str
    api_key: str
    created_at: str


class ApiKeyListItem(BaseModel):
    id: str
    name: Optional[str] = None
    prefix: str
    created_at: str
    last_used_at: Optional[str] = None
    revoked_at: Optional[str] = None


class ApiKeyListResponse(BaseModel):
    count: int
    items: list[ApiKeyListItem]

