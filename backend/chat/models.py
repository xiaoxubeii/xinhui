# -*- coding: utf-8 -*-
"""Chat — Pydantic models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from ..artifacts.models import ArtifactCategory, ArtifactListItem


AgentId = Literal["report", "analysis", "health", "diet", "clinical", "prescription"]


class ChatSessionCreateRequest(BaseModel):
    agent_id: AgentId
    title: str = Field(default="新会话", max_length=64)


class ChatSessionSummary(BaseModel):
    id: str
    agent_id: AgentId
    title: str
    created_at: str
    updated_at: str


class ChatSessionListResponse(BaseModel):
    count: int
    items: list[ChatSessionSummary]


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class ChatSessionDetailResponse(BaseModel):
    id: str
    agent_id: AgentId
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessage]
    artifacts: list[ArtifactListItem]


class ChatMessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10_000)
    # Optional: attach additional artifacts (on top of session attachments) for this turn.
    attachments: Optional[list[str]] = None


class ChatMessageCreateResponse(BaseModel):
    status: str
    answer: str

