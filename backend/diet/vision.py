# -*- coding: utf-8 -*-
"""Diet — Vision model call (OpenAI-compatible chat/completions)."""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import httpx

from ..config import settings
from .models import DietVisionRawResult, NutritionTotals
from .storage import compute_totals


@dataclass(frozen=True)
class VisionSettings:
    base_url: str
    api_key: str
    model: str
    timeout: float
    temperature: float
    max_tokens: int


def resolve_vision_settings() -> VisionSettings:
    base_url = (os.environ.get("DIET_VISION_BASE_URL") or settings.qwen_base_url).rstrip("/")
    api_key = os.environ.get("DIET_VISION_API_KEY") or settings.qwen_api_key or ""
    if not api_key:
        raise ValueError("DIET_VISION_API_KEY (or QWEN_API_KEY fallback) not set")
    model = os.environ.get("DIET_VISION_MODEL") or "qwen-vl-max"
    timeout = float(os.environ.get("DIET_VISION_TIMEOUT") or settings.qwen_timeout)
    temperature = float(os.environ.get("DIET_VISION_TEMPERATURE") or 0.2)
    max_tokens = int(os.environ.get("DIET_VISION_MAX_TOKENS") or 800)
    return VisionSettings(
        base_url=base_url,
        api_key=api_key,
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
    url = cfg.base_url
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"

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
        "model": cfg.model,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": _data_url(image_mime, image_bytes)}},
                ],
            },
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg.api_key}",
    }

    with httpx.Client(timeout=cfg.timeout) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
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

