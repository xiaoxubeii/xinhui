# -*- coding: utf-8 -*-
"""Artifacts — API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from ..auth.security import get_current_user
from .models import (
    ArtifactCategory,
    ArtifactDetailResponse,
    ArtifactListItem,
    ArtifactListResponse,
    ArtifactUploadResponse,
)
from .storage import (
    create_artifact_from_upload,
    delete_artifact,
    get_artifact_original_path,
    get_artifact_row,
    list_artifacts,
    read_artifact_extracted_text,
    read_artifact_parsed_json,
)

router = APIRouter(prefix="/api/artifacts", tags=["Artifacts"])


@router.post("/upload", response_model=ArtifactUploadResponse, summary="Upload an artifact (persisted)")
def upload_artifact(
    category: ArtifactCategory = Form(...),
    title: str | None = Form(default=None),
    attach_session_id: str | None = Form(default=None),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    row = create_artifact_from_upload(
        user_id=user["id"],
        category=category.value,
        title=title,
        upload=file,
        attach_session_id=attach_session_id,
    )
    return ArtifactUploadResponse(
        id=row["id"],
        category=ArtifactCategory(row["category"]),
        title=row.get("title"),
        filename=row["filename"],
        content_type=row["content_type"],
        size_bytes=row["size_bytes"],
        sha256=row["sha256"],
        created_at=row["created_at"],
        extracted_preview=row.get("extracted_preview"),
        has_parsed_json=bool(row.get("has_parsed_json")),
    )


@router.get("", response_model=ArtifactListResponse, summary="List my artifacts")
def list_my_artifacts(
    category: ArtifactCategory | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    rows = list_artifacts(
        user_id=user["id"],
        category=category.value if category else None,
        q=q,
        limit=limit,
        offset=offset,
    )
    items = [
        ArtifactListItem(
            id=r["id"],
            category=ArtifactCategory(r["category"]),
            title=r.get("title"),
            filename=r["filename"],
            content_type=r["content_type"],
            size_bytes=int(r["size_bytes"]),
            created_at=r["created_at"],
            has_extracted_text=bool(r.get("extracted_text_relpath")),
            has_parsed_json=bool(r.get("parsed_json_relpath")),
        )
        for r in rows
    ]
    return ArtifactListResponse(count=len(items), items=items)


@router.get("/{artifact_id}", response_model=ArtifactDetailResponse, summary="Get artifact metadata + extracted/parsed preview")
def get_artifact_detail(artifact_id: str, user: dict = Depends(get_current_user)):
    row = get_artifact_row(user_id=user["id"], artifact_id=artifact_id)
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")
    extracted = read_artifact_extracted_text(row)
    parsed = read_artifact_parsed_json(row)
    return ArtifactDetailResponse(
        id=row["id"],
        category=ArtifactCategory(row["category"]),
        title=row.get("title"),
        filename=row["filename"],
        content_type=row["content_type"],
        size_bytes=int(row["size_bytes"]),
        sha256=row["sha256"],
        created_at=row["created_at"],
        extracted_text=extracted,
        parsed_json=parsed,
    )


@router.get("/{artifact_id}/download", summary="Download original artifact file")
def download_artifact(artifact_id: str, user: dict = Depends(get_current_user)):
    row = get_artifact_row(user_id=user["id"], artifact_id=artifact_id)
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = get_artifact_original_path(row)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(
        str(path),
        media_type=row.get("content_type") or "application/octet-stream",
        filename=row.get("filename") or path.name,
    )


@router.delete("/{artifact_id}", summary="Delete an artifact")
def delete_artifact_api(artifact_id: str, user: dict = Depends(get_current_user)):
    ok = delete_artifact(user_id=user["id"], artifact_id=artifact_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"status": "ok", "artifact_id": artifact_id}

