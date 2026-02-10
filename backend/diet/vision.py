# -*- coding: utf-8 -*-
"""Diet — Vision model call via OpenCode session API."""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

import httpx

from ..config import settings
from .models import DietVisionRawResult, NutritionTotals
from .storage import compute_totals


@dataclass(frozen=True)
class VisionSettings:
    base_url: str
    model: str
    timeout: float
    temperature: float
    max_tokens: int


def _strip_jsonc(text: str) -> str:
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\\*.*?\\*/", "", text, flags=re.DOTALL)
    return text


def _resolve_default_model() -> str | None:
    config_path = settings.agent_config_path
    if not config_path or not config_path.exists():
        return None
    try:
        raw = config_path.read_text(encoding="utf-8")
        parsed = json.loads(_strip_jsonc(raw))
    except Exception:
        return None
    model = parsed.get("model") or parsed.get("agent", {}).get("model")
    return model if isinstance(model, str) and model else None


def resolve_vision_settings() -> VisionSettings:
    base_url = (os.environ.get("DIET_VISION_BASE_URL") or settings.opencode_base_url).rstrip("/")
    model = os.environ.get("DIET_VISION_MODEL") or _resolve_default_model() or "opencode/minimax-m2.1-free"
    timeout = float(os.environ.get("DIET_VISION_TIMEOUT") or settings.qwen_timeout)
    temperature = float(os.environ.get("DIET_VISION_TEMPERATURE") or 0.2)
    max_tokens = int(os.environ.get("DIET_VISION_MAX_TOKENS") or 800)
    return VisionSettings(
        base_url=base_url,
        model=model,
        timeout=timeout,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _extract_json(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model output does not contain a JSON object")
    return cleaned[start : end + 1]


def _data_url(mime: str, image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


def recognize_food(
    *,
    image_bytes: bytes,
    image_mime: str,
    locale: str | None,
) -> Tuple[DietVisionRawResult, str]:
    cfg = resolve_vision_settings()
    base = cfg.base_url.rstrip("/")
    parsed = urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}"
    session_url = f"{base}/session"
    if base != root:
        session_url = f"{root}/session"

    locale_str = locale or "zh-CN"

    system_prompt = (
        "You are a nutrition assistant. Return STRICT JSON only (no markdown). "
        "Estimate food type and nutrition for the portion shown. "
        "If unsure, use low confidence and add warnings; do NOT fabricate precise numbers."
    )
    user_prompt = (
        f"Locale: {locale_str}\n"
        "Task:\n"
        "1) Identify all foods in the photo.\n"
        "2) Estimate portion and grams.\n"
        "3) Estimate nutrition for the consumed portion: calories_kcal, protein_g, carbs_g, fat_g.\n"
        "\n"
        "Output JSON schema (STRICT):\n"
        "{\n"
        '  "items": [\n'
        "    {\n"
        '      "name": "string",\n'
        '      "portion": "string|null",\n'
        '      "grams": number|null,\n'
        '      "calories_kcal": number|null,\n'
        '      "protein_g": number|null,\n'
        '      "carbs_g": number|null,\n'
        '      "fat_g": number|null,\n'
        '      "confidence": number|null\n'
        "    }\n"
        "  ],\n"
        '  "totals": {"calories_kcal": number, "protein_g": number, "carbs_g": number, "fat_g": number} | null,\n'
        '  "warnings": ["string"]\n'
        "}\n"
    )

    payload: Dict[str, Any] = {
        "system": system_prompt,
        "parts": [
            {"type": "text", "text": user_prompt},
            {
                "type": "file",
                "mime": image_mime,
                "filename": "meal",
                "url": _data_url(image_mime, image_bytes),
            },
        ],
    }
    if "/" in cfg.model:
        provider_id, model_id = cfg.model.split("/", 1)
        if provider_id and model_id:
            payload["model"] = {"providerID": provider_id, "modelID": model_id}

    headers = {
        "Content-Type": "application/json",
        "x-opencode-directory": str(settings.opencode_directory),
    }

    data = None
    last_error: Exception | None = None
    with httpx.Client(timeout=cfg.timeout, follow_redirects=True) as client:
        try:
            session_resp = client.post(session_url, headers=headers, json={"title": "diet-vision"})
            session_resp.raise_for_status()
            session = session_resp.json()
            session_id = session.get("id") or session.get("session_id")
            if not session_id:
                raise ValueError("OpenCode session id missing")
            msg_url = f"{session_url}/{session_id}/message"
            resp = client.post(msg_url, headers=headers, json=payload)
            content_type = resp.headers.get("content-type") or ""
            if resp.status_code >= 400:
                resp.raise_for_status()
            if "text/html" in content_type:
                raise ValueError("OpenCode API returned HTML")
            data = resp.json()
        except Exception as exc:
            last_error = exc

    if data is None:
        raise ValueError(f"OpenCode vision call failed: {last_error}")

    parts = data.get("parts") if isinstance(data, dict) else None
    content = ""
    if isinstance(parts, list):
        content = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict) and part.get("type") == "text"
        )
    if not content and isinstance(data, dict):
        info = data.get("info")
        if isinstance(info, dict):
            msg_parts = info.get("parts")
            if isinstance(msg_parts, list):
                content = "".join(
                    part.get("text", "")
                    for part in msg_parts
                    if isinstance(part, dict) and part.get("type") == "text"
                )
    json_str = _extract_json(content or "")
    parsed = json.loads(json_str)

    # Accept extra fields but validate known ones.
    known = {
        "items": parsed.get("items", []),
        "totals": parsed.get("totals"),
        "warnings": parsed.get("warnings", []),
        "extra": {k: v for k, v in parsed.items() if k not in {"items", "totals", "warnings"}},
    }
    result = DietVisionRawResult.model_validate(known)

    # Ensure totals exist; if model does not provide totals, compute from items.
    if result.totals is None:
        result.totals = compute_totals([i.model_dump() for i in result.items])
    else:
        # Normalize rounding.
        result.totals = NutritionTotals(
            calories_kcal=round(result.totals.calories_kcal, 1),
            protein_g=round(result.totals.protein_g, 1),
            carbs_g=round(result.totals.carbs_g, 1),
            fat_g=round(result.totals.fat_g, 1),
        )

    return result, cfg.model
