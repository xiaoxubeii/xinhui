# -*- coding: utf-8 -*-
"""Artifacts — models and enums."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ArtifactCategory(str, Enum):
    cpet_report = "cpet_report"
    exercise_data = "exercise_data"
    health_data = "health_data"
    diet_data = "diet_data"
    lab_report = "lab_report"
    imaging_report = "imaging_report"
    other = "other"


class ArtifactUploadResponse(BaseModel):
    id: str
    category: ArtifactCategory
    title: Optional[str] = None
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: str
    extracted_preview: Optional[str] = None
    has_parsed_json: bool = False


class ArtifactListItem(BaseModel):
    id: str
    category: ArtifactCategory
    title: Optional[str] = None
    filename: str
    content_type: str
    size_bytes: int
    created_at: str
    has_extracted_text: bool = False
    has_parsed_json: bool = False


class ArtifactListResponse(BaseModel):
    count: int
    items: list[ArtifactListItem]


class ArtifactDetailResponse(BaseModel):
    id: str
    category: ArtifactCategory
    title: Optional[str] = None
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: str
    extracted_text: Optional[str] = Field(default=None, description="Truncated extracted text")
    parsed_json: Optional[dict] = None

