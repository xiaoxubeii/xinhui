# -*- coding: utf-8 -*-
"""OpenCode API helpers for the chat endpoint."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from ..config import settings


def _headers() -> dict[str, str]:
    return {"x-opencode-directory": str(settings.opencode_directory)}


async def create_session(*, title: str) -> str:
    base = settings.opencode_base_url.rstrip("/")
    url = f"{base}/session"
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.post(url, json={"title": title}, headers=_headers())
        # Some deployments may serve CPET OpenCode behind a subpath; fallback to root if we get HTML.
        if resp.status_code >= 400 and "text/html" in (resp.headers.get("content-type") or ""):
            parsed = urlparse(base)
            root = f"{parsed.scheme}://{parsed.netloc}"
            resp = await client.post(f"{root}/session", json={"title": title}, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("id") or data.get("session_id") or "")


async def send_message(
    *,
    session_id: str,
    agent: str,
    content: str,
    stream: bool = True,
) -> tuple[httpx.AsyncClient, httpx.Response]:
    base = settings.opencode_base_url.rstrip("/")
    url = f"{base}/session/{session_id}/message"
    headers = _headers()
    headers["Accept"] = "text/event-stream, application/json" if stream else "application/json"
    client = httpx.AsyncClient(timeout=None, follow_redirects=True)
    req = client.build_request(
        "POST",
        url,
        headers=headers,
        json={"agent": agent, "parts": [{"type": "text", "text": content}]},
    )
    resp = await client.send(req, stream=stream)
    return client, resp
