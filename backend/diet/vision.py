# -*- coding: utf-8 -*-
"""Diet — Vision model call via OpenCode session API."""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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


def _load_opencode_config() -> Dict[str, Any] | None:
    candidates = []
    config_path = settings.agent_config_path
    if config_path:
        candidates.append(config_path)
    opencode_dir = settings.opencode_directory
    candidates.extend(
        [
            opencode_dir / ".opencode" / "opencode.jsonc",
            opencode_dir / ".opencode" / "opencode.json",
        ]
    )
    for path in candidates:
        if not path or not path.exists():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            return json.loads(_strip_jsonc(raw))
        except Exception:
            continue
    return None


def _resolve_default_model(config: Dict[str, Any] | None) -> str | None:
    if not config:
        return None
    model = config.get("model") or config.get("agent", {}).get("model")
    return model if isinstance(model, str) and model else None


def _resolve_vision_model(config: Dict[str, Any] | None) -> str | None:
    if not config:
        return None
    for key in ("diet_vision_model", "vision_model"):
        value = config.get(key)
        if isinstance(value, str) and value:
            return value
    diet = config.get("diet")
    if isinstance(diet, dict):
        for key in ("vision_model", "model"):
            value = diet.get(key)
            if isinstance(value, str) and value:
                return value
    vision = config.get("vision")
    if isinstance(vision, dict):
        for key in ("model", "vision_model"):
            value = vision.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def resolve_vision_settings() -> VisionSettings:
    base_url = (os.environ.get("DIET_VISION_BASE_URL") or settings.opencode_base_url).rstrip("/")
    config = _load_opencode_config()
    model = (
        os.environ.get("DIET_VISION_MODEL")
        or _resolve_vision_model(config)
        or _resolve_default_model(config)
        or "opencode/minimax-m2.1-free"
    )
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


_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _coerce_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        m = _NUM_RE.search(s.replace(",", ""))
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None
    return None


def _as_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    if isinstance(value, list):
        out: List[str] = []
        for x in value:
            if x is None:
                continue
            if isinstance(x, str):
                s = x.strip()
            else:
                s = str(x).strip()
            if s:
                out.append(s)
        return out
    if isinstance(value, dict):
        for k in ("warnings", "warning", "message", "detail", "error", "text"):
            v = value.get(k)
            if isinstance(v, str) and v.strip():
                return [v.strip()]
    s = str(value).strip()
    return [s] if s else []


def _normalize_totals(totals: Any) -> Optional[Dict[str, float]]:
    """Normalize totals keys to NutritionTotals schema if possible."""
    if totals is None:
        return None
    if not isinstance(totals, dict):
        return None

    key_map = {
        # Calories
        "calories": "calories_kcal",
        "calorie": "calories_kcal",
        "kcal": "calories_kcal",
        "energy": "calories_kcal",
        "energy_kcal": "calories_kcal",
        # Protein
        "protein": "protein_g",
        # Carbs
        "carbohydrates": "carbs_g",
        "carbs": "carbs_g",
        "carb": "carbs_g",
        # Fat
        "fat": "fat_g",
        "lipid": "fat_g",
    }
    allowed = {"calories_kcal", "protein_g", "carbs_g", "fat_g"}
    out: Dict[str, float] = {}
    for k, v in totals.items():
        if not isinstance(k, str):
            continue
        kk = key_map.get(k, k)
        if kk not in allowed:
            continue
        fv = _coerce_float(v)
        if fv is None:
            continue
        out[kk] = max(0.0, fv)
    return out or None


def _first_present(obj: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in obj:
            return obj.get(k)
    return None


def _normalize_items(items: Any) -> List[Dict[str, Any]]:
    """Normalize item schema to FoodItem as much as possible (best-effort)."""
    if not isinstance(items, list):
        return []
    out: List[Dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue

        name = _first_present(raw, ["name", "food", "item", "dish", "title"])
        if not isinstance(name, str):
            name = str(name) if name is not None else ""
        name = name.strip() or "unknown"

        portion = _first_present(raw, ["portion", "serving", "amount", "size", "quantity"])
        portion_str: Optional[str] = None
        if isinstance(portion, str):
            portion = portion.strip()
            if portion:
                portion_str = portion

        grams = _coerce_float(_first_present(raw, ["grams", "gram", "weight_g", "weight", "g"]))

        def pick_num(keys: List[str]) -> Optional[float]:
            for k in keys:
                if k in raw:
                    val = _coerce_float(raw.get(k))
                    if val is not None:
                        return val
            return None

        calories = pick_num(["calories_kcal", "calories", "kcal", "energy_kcal", "energy"])
        protein = pick_num(["protein_g", "protein"])
        carbs = pick_num(["carbs_g", "carbs", "carbohydrates"])
        fat = pick_num(["fat_g", "fat", "lipid"])

        confidence = pick_num(["confidence", "conf", "score"])
        if confidence is not None and confidence > 1 and confidence <= 100:
            confidence = confidence / 100.0
        if confidence is not None:
            confidence = max(0.0, min(1.0, confidence))

        item: Dict[str, Any] = {"name": name}
        if portion_str is not None:
            item["portion"] = portion_str
        if grams is not None:
            item["grams"] = max(0.0, grams)
        if calories is not None:
            item["calories_kcal"] = max(0.0, calories)
        if protein is not None:
            item["protein_g"] = max(0.0, protein)
        if carbs is not None:
            item["carbs_g"] = max(0.0, carbs)
        if fat is not None:
            item["fat_g"] = max(0.0, fat)
        if confidence is not None:
            item["confidence"] = confidence
        out.append(item)
    return out


def _normalize_parsed(parsed: Dict[str, Any]) -> Dict[str, Any]:
    items_raw = parsed.get("items")
    if items_raw is None:
        items_raw = parsed.get("foods") or parsed.get("food")
    totals_raw = parsed.get("totals")
    if totals_raw is None:
        totals_raw = parsed.get("total")
    warnings_raw = parsed.get("warnings")
    if warnings_raw is None:
        warnings_raw = parsed.get("warning")

    items = _normalize_items(items_raw)
    totals = _normalize_totals(totals_raw)
    warnings = _as_str_list(warnings_raw)

    return {
        "items": items,
        "totals": totals,
        "warnings": warnings,
        "extra": {k: v for k, v in parsed.items() if k not in {"items", "foods", "food", "totals", "total", "warnings", "warning"}},
    }


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
    parsed: Dict[str, Any]
    try:
        json_str = _extract_json(content or "")
        parsed = json.loads(json_str)
    except Exception as exc:
        # Don't fail the whole request when the model returns non-JSON (or empty) output.
        # The iOS review screen can still let users manually fill in food items.
        parsed = {
            "items": [],
            "totals": None,
            "warnings": [
                "模型输出无法解析，请手动添加/修改食物条目后再保存。",
            ],
            "raw_text": (content or "")[:800],
            "parse_error": str(exc),
        }

    known = _normalize_parsed(parsed)
    try:
        result = DietVisionRawResult.model_validate(known)
    except Exception as exc:
        # If validation still fails, degrade gracefully.
        fallback = {
            "items": [],
            "totals": None,
            "warnings": [
                "模型输出格式异常，请手动添加/修改食物条目后再保存。",
            ],
            "extra": {
                "parse_error": str(exc),
                "raw_text": (content or "")[:800],
            },
        }
        result = DietVisionRawResult.model_validate(fallback)

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
