# -*- coding: utf-8 -*-
"""Chat — API endpoints (sessions/messages)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..artifacts.models import ArtifactCategory, ArtifactListItem
from ..auth.security import get_current_user
from .context import build_agent_context
from .models import (
    ChatMessage,
    ChatMessageCreateRequest,
    ChatMessageCreateResponse,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatSessionSummary,
)
from .opencode import create_session as opencode_create_session
from .opencode import send_message as opencode_send_message
from .storage import (
    append_message,
    attach_artifact,
    create_session,
    detach_artifact,
    list_attached_artifacts,
    list_messages,
    list_sessions,
    require_session,
    set_opencode_session_id,
    update_session_title_if_first_user_message,
)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


def _artifact_item(row: Dict[str, Any]) -> ArtifactListItem:
    return ArtifactListItem(
        id=row["id"],
        category=ArtifactCategory(row["category"]),
        title=row.get("title"),
        filename=row.get("filename"),
        content_type=row.get("content_type"),
        size_bytes=int(row.get("size_bytes") or 0),
        created_at=row.get("created_at") or "",
        has_extracted_text=bool(row.get("extracted_text_relpath")),
        has_parsed_json=bool(row.get("parsed_json_relpath")),
    )


@router.post("/sessions", response_model=ChatSessionSummary, summary="Create a chat session")
def create_chat_session(request: ChatSessionCreateRequest, user: dict = Depends(get_current_user)):
    row = create_session(user_id=user["id"], agent_id=request.agent_id, title=request.title)
    return ChatSessionSummary(
        id=row["id"],
        agent_id=row["agent_id"],  # type: ignore[arg-type]
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/sessions", response_model=ChatSessionListResponse, summary="List my sessions")
def list_chat_sessions(
    agent_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    rows = list_sessions(user_id=user["id"], agent_id=agent_id, limit=limit, offset=offset)
    items = [
        ChatSessionSummary(
            id=r["id"],
            agent_id=r["agent_id"],  # type: ignore[arg-type]
            title=r["title"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]
    return ChatSessionListResponse(count=len(items), items=items)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse, summary="Get session detail (messages + attachments)")
def get_chat_session_detail(session_id: str, user: dict = Depends(get_current_user)):
    session = require_session(user_id=user["id"], session_id=session_id)
    messages = list_messages(session_id=session_id, limit=500)
    artifacts = list_attached_artifacts(user_id=user["id"], session_id=session_id)
    return ChatSessionDetailResponse(
        id=session["id"],
        agent_id=session["agent_id"],  # type: ignore[arg-type]
        title=session["title"],
        created_at=session["created_at"],
        updated_at=session["updated_at"],
        messages=[
            ChatMessage(
                id=m["id"],
                role=m["role"],  # type: ignore[arg-type]
                content=m["content"],
                created_at=m["created_at"],
            )
            for m in messages
        ],
        artifacts=[_artifact_item(a) for a in artifacts],
    )


@router.post("/sessions/{session_id}/artifacts/{artifact_id}", summary="Attach an artifact to a session")
def attach_artifact_api(session_id: str, artifact_id: str, user: dict = Depends(get_current_user)):
    attach_artifact(user_id=user["id"], session_id=session_id, artifact_id=artifact_id)
    return {"status": "ok"}


@router.delete("/sessions/{session_id}/artifacts/{artifact_id}", summary="Detach an artifact from a session")
def detach_artifact_api(session_id: str, artifact_id: str, user: dict = Depends(get_current_user)):
    detach_artifact(user_id=user["id"], session_id=session_id, artifact_id=artifact_id)
    return {"status": "ok"}


def _collect_text_parts(parts: Any) -> str:
    if not isinstance(parts, list):
        return ""
    out: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
            out.append(part["text"])
    return "".join(out)


def _extract_opencode_delta(event: Any) -> str:
    if not isinstance(event, dict):
        return ""
    if isinstance(event.get("answer"), str):
        return event["answer"]
    parts = event.get("parts")
    if isinstance(parts, list):
        return _collect_text_parts(parts)
    msg = event.get("message")
    if isinstance(msg, dict) and isinstance(msg.get("parts"), list):
        return _collect_text_parts(msg.get("parts"))
    data = event.get("data")
    if isinstance(data, dict) and isinstance(data.get("parts"), list):
        return _collect_text_parts(data.get("parts"))
    return ""


def _extract_opencode_error(event: Any) -> str:
    if not isinstance(event, dict):
        return ""
    err = event.get("error")
    if isinstance(err, dict):
        msg = err.get("message") or err.get("detail") or err.get("error")
        if isinstance(msg, str):
            return msg
    info = event.get("info")
    if isinstance(info, dict):
        err = info.get("error")
        if isinstance(err, dict):
            data = err.get("data")
            if isinstance(data, dict):
                msg = data.get("message")
                if isinstance(msg, str):
                    return msg
            msg = err.get("message")
            if isinstance(msg, str):
                return msg
    return ""


@router.post("/sessions/{session_id}/message", summary="Send a message (streams SSE if requested)")
async def send_chat_message(
    session_id: str,
    request_body: ChatMessageCreateRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    session = require_session(user_id=user["id"], session_id=session_id)

    content = request_body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Empty content")

    # Persist user message first.
    append_message(session_id=session_id, role="user", content=content)
    update_session_title_if_first_user_message(session_id=session_id, title=content[:16])

    # Assemble context (includes auto history data + artifacts).
    ctx = build_agent_context(
        user_id=user["id"],
        agent_id=session["agent_id"],
        session_id=session_id,
        extra_artifact_ids=request_body.attachments or None,
    )

    full_prompt = f"Context (JSON):\n{json.dumps(ctx, ensure_ascii=False)}\n\nQuestion:\n{content}"
    wants_stream = "text/event-stream" in (request.headers.get("accept") or "")

    # Ensure OpenCode session id.
    opencode_id = session.get("opencode_session_id")
    if not opencode_id:
        try:
            opencode_id = await opencode_create_session(title=session["title"])
        except Exception:
            opencode_id = ""
        if opencode_id:
            set_opencode_session_id(session_id=session_id, opencode_session_id=opencode_id)

    if not opencode_id:
        raise HTTPException(status_code=502, detail="OpenCode session unavailable")

    try:
        client, resp = await opencode_send_message(
            session_id=opencode_id,
            agent=str(session["agent_id"]),
            content=full_prompt,
            stream=wants_stream,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenCode send failed: {exc}") from exc

    if resp.status_code >= 400:
        raw = b""
        try:
            raw = await resp.aread()
        finally:
            try:
                await resp.aclose()
            finally:
                await client.aclose()
        err_msg = ""
        if raw:
            try:
                payload = json.loads(raw.decode("utf-8", errors="ignore"))
                err_msg = _extract_opencode_error(payload)
                if not err_msg and isinstance(payload, dict):
                    err_msg = payload.get("message") or payload.get("detail") or ""
            except Exception:
                err_msg = raw.decode("utf-8", errors="ignore").strip()
        detail = f"OpenCode error: {resp.status_code}"
        if err_msg:
            detail = f"{detail} - {err_msg}"
        raise HTTPException(status_code=502, detail=detail)

    content_type = resp.headers.get("content-type") or ""
    if wants_stream and "text/event-stream" in content_type:
        async def stream():
            buffer = ""
            full_text = ""
            try:
                async for chunk in resp.aiter_raw():
                    if not chunk:
                        continue
                    try:
                        buffer += chunk.decode("utf-8", errors="ignore")
                        lines = buffer.split("\n")
                        buffer = lines.pop() if lines else ""
                        for line in lines:
                            if not line.startswith("data:"):
                                continue
                            json_str = line[5:].strip()
                            if not json_str or json_str == "[DONE]":
                                continue
                            try:
                                event = json.loads(json_str)
                                delta = _extract_opencode_delta(event)
                                if delta:
                                    full_text += delta
                            except Exception:
                                continue
                    except Exception:
                        pass
                    yield chunk
                # Process trailing buffer as a line.
                if buffer.startswith("data:"):
                    json_str = buffer[5:].strip()
                    if json_str and json_str != "[DONE]":
                        try:
                            event = json.loads(json_str)
                            delta = _extract_opencode_delta(event)
                            if delta:
                                full_text += delta
                        except Exception:
                            pass
            finally:
                try:
                    await resp.aclose()
                finally:
                    await client.aclose()
                if full_text.strip():
                    append_message(session_id=session_id, role="assistant", content=full_text)
        return StreamingResponse(stream(), media_type="text/event-stream")

    # Non-stream response (JSON-ish from OpenCode).
    try:
        raw = await resp.aread()
    finally:
        try:
            await resp.aclose()
        finally:
            await client.aclose()

    answer_text = ""
    try:
        payload = json.loads(raw.decode("utf-8", errors="ignore"))
        answer_text = _extract_opencode_delta(payload)
    except Exception:
        answer_text = raw.decode("utf-8", errors="ignore").strip()

    if not answer_text:
        raise HTTPException(status_code=502, detail="OpenCode returned empty response")

    append_message(session_id=session_id, role="assistant", content=answer_text)
    return JSONResponse(content=ChatMessageCreateResponse(status="ok", answer=answer_text).model_dump())
