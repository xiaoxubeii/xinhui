# -*- coding: utf-8 -*-
"""Diet — Vision model call via OpenCode session API."""

from __future__ import annotations

import ast
import base64
import json
import logging
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
    agent: str


def _remove_trailing_commas(text: str) -> str:
    """Remove trailing commas in JSON/JSONC while preserving string literals."""
    out: list[str] = []
    in_str = False
    escaped = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_str:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "\"":
                in_str = False
            i += 1
            continue

        if ch == "\"":
            in_str = True
            out.append(ch)
            i += 1
            continue

        if ch == ",":
            j = i + 1
            while j < len(text) and text[j] in " \t\r\n":
                j += 1
            if j < len(text) and text[j] in "}]":
                i += 1
                continue

        out.append(ch)
        i += 1
    return "".join(out)


def _strip_jsonc(text: str) -> str:
    """Strip JSONC comments without breaking URLs/strings, then remove trailing commas."""
    out: list[str] = []
    in_str = False
    escaped = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_str:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "\"":
                in_str = False
            i += 1
            continue

        if ch == "\"":
            in_str = True
            out.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == "/":
                i += 2
                while i < len(text) and text[i] not in "\n\r":
                    i += 1
                continue
            if nxt == "*":
                i += 2
                while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2 if i + 1 < len(text) else 1
                continue

        out.append(ch)
        i += 1

    return _remove_trailing_commas("".join(out))


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


def resolve_vision_settings() -> VisionSettings:
    base_url = (os.environ.get("DIET_VISION_BASE_URL") or settings.opencode_base_url).rstrip("/")
    # NOTE: Do not fall back to OpenCode's global `model` config, which is often text-only.
    # If the caller doesn't set DIET_VISION_MODEL, default to a known image-capable model.
    model = (os.environ.get("DIET_VISION_MODEL") or "").strip() or "opencode/kimi-k2.5-free"
    timeout = float(os.environ.get("DIET_VISION_TIMEOUT") or settings.qwen_timeout)
    # Use a built-in agent by default to avoid depending on file-watcher reloads.
    # (Project default agent is often "clinical", which can break JSON-only output.)
    agent = (os.environ.get("DIET_VISION_AGENT") or "general").strip() or "general"
    return VisionSettings(
        base_url=base_url,
        model=model,
        timeout=timeout,
        agent=agent,
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


def _iter_json_object_candidates(text: str) -> list[str]:
    """Extract balanced {...} candidates from arbitrary text.

    Models sometimes wrap JSON with extra prose or include multiple JSON objects.
    We scan for balanced braces while respecting string literals.
    """
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    candidates: list[str] = []
    in_str = False
    escaped = False
    depth = 0
    start_idx: int | None = None

    for i, ch in enumerate(cleaned):
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "\"":
                in_str = False
            continue

        if ch == "\"":
            in_str = True
            continue

        if ch == "{":
            if depth == 0:
                start_idx = i
            depth += 1
            continue

        if ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start_idx is not None:
                    candidates.append(cleaned[start_idx : i + 1])
                    start_idx = None
            continue

    return candidates


def _sanitize_json_like(text: str) -> str:
    # Common LLM output issues: full-width punctuation, curly quotes, trailing commas,
    # and non-finite floats.
    cleaned = text
    cleaned = cleaned.replace("：", ":").replace("，", ",")
    cleaned = cleaned.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
    cleaned = _remove_trailing_commas(cleaned)
    cleaned = re.sub(r"\bNaN\b", "null", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b-?Infinity\b", "null", cleaned, flags=re.IGNORECASE)
    return cleaned


def _parse_model_output_json(content: str) -> Dict[str, Any]:
    last_error: Exception | None = None

    for candidate in _iter_json_object_candidates(content):
        sanitized = _sanitize_json_like(candidate)
        for attempt in (candidate, sanitized):
            try:
                parsed = json.loads(attempt)
                if isinstance(parsed, dict):
                    return parsed
            except Exception as exc:
                last_error = exc

        # As a fallback, try parsing Python-literal-ish dicts (single quotes/None/True/False).
        for py_candidate in (candidate, sanitized):
            try:
                py = py_candidate
                py = re.sub(r"\bnull\b", "None", py, flags=re.IGNORECASE)
                py = re.sub(r"\btrue\b", "True", py, flags=re.IGNORECASE)
                py = re.sub(r"\bfalse\b", "False", py, flags=re.IGNORECASE)
                parsed = ast.literal_eval(py)
                if isinstance(parsed, dict):
                    return parsed
            except Exception as exc:
                last_error = exc

    # Keep previous behavior for minimal changes in error messaging.
    try:
        return json.loads(_sanitize_json_like(_extract_json(content)))
    except Exception as exc:
        last_error = exc

    raise ValueError(f"Failed to parse model JSON: {last_error}") from last_error


def _concat_text_parts(parts: object) -> str:
    if not isinstance(parts, list):
        return ""
    out: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        ptype = part.get("type")
        if ptype and ptype not in {"text", "output_text"}:
            continue
        for key in ("text", "content", "value"):
            val = part.get(key)
            if isinstance(val, str) and val:
                out.append(val)
                break
    return "".join(out)


def _extract_text_from_opencode_response(data: object) -> str:
    """Support OpenCode 'parts' responses and OpenAI-compatible 'choices' responses."""
    if not isinstance(data, dict):
        return ""

    parts = data.get("parts")
    content = _concat_text_parts(parts)
    if content:
        return content

    info = data.get("info")
    if isinstance(info, dict):
        content = _concat_text_parts(info.get("parts"))
        if content:
            return content
        maybe = info.get("content")
        if isinstance(maybe, str) and maybe:
            return maybe

    message = data.get("message")
    if isinstance(message, dict):
        content = _concat_text_parts(message.get("parts"))
        if content:
            return content
        maybe = message.get("content")
        if isinstance(maybe, str) and maybe:
            return maybe

    choices = data.get("choices")
    if isinstance(choices, list):
        out: list[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            msg = choice.get("message")
            if isinstance(msg, dict):
                maybe = msg.get("content")
                if isinstance(maybe, str) and maybe:
                    out.append(maybe)
            delta = choice.get("delta")
            if isinstance(delta, dict):
                maybe = delta.get("content")
                if isinstance(maybe, str) and maybe:
                    out.append(maybe)
            maybe_text = choice.get("text")
            if isinstance(maybe_text, str) and maybe_text:
                out.append(maybe_text)
        if out:
            return "".join(out)

    return ""


def _extract_error_from_opencode_response(data: object) -> str | None:
    """Extract a human-readable error message from an OpenCode message response."""
    if not isinstance(data, dict):
        return None

    def pick_str(value: object) -> str | None:
        if isinstance(value, str):
            s = value.strip()
            return s if s else None
        return None

    def msg_from_json_str(raw: str) -> str | None:
        raw = raw.strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except Exception:
            return None
        if isinstance(parsed, dict):
            err = parsed.get("error")
            if isinstance(err, dict):
                msg = pick_str(err.get("message"))
                if msg:
                    return msg
            msg = pick_str(parsed.get("message")) or pick_str(parsed.get("detail"))
            if msg:
                return msg
        return None

    def coerce(err_obj: object) -> str | None:
        if not isinstance(err_obj, dict):
            return None
        name = pick_str(err_obj.get("name")) or "OpenCodeError"
        data_obj = err_obj.get("data")
        status = None
        message = pick_str(err_obj.get("message"))

        if isinstance(data_obj, dict):
            status = data_obj.get("statusCode") if isinstance(data_obj.get("statusCode"), int) else None
            message = pick_str(data_obj.get("message")) or message

            # When providers return a JSON error payload, OpenCode often stores it as a string.
            response_body = pick_str(data_obj.get("responseBody"))
            if response_body:
                message = msg_from_json_str(response_body) or message

            meta = data_obj.get("metadata")
            if isinstance(meta, dict):
                raw = pick_str(meta.get("raw"))
                if raw:
                    message = msg_from_json_str(raw) or message

        if not message:
            return None
        prefix = f"{name}"
        if status is not None:
            prefix = f"{prefix} ({status})"
        return f"{prefix}: {message}"

    info = data.get("info")
    if isinstance(info, dict):
        msg = coerce(info.get("error"))
        if msg:
            return msg

    msg = coerce(data.get("error"))
    if msg:
        return msg

    return None


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
    log = logging.getLogger(__name__)
    base = cfg.base_url.rstrip("/")
    parsed = urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}"
    session_url = f"{base}/session"
    if base != root:
        session_url = f"{root}/session"

    locale_str = locale or "zh-CN"

    system_prompt = (
        "You are a nutrition assistant. Return STRICT JSON only. "
        "Do NOT wrap in markdown or code fences. "
        "Output MUST start with '{' and end with '}'. "
        "Use double quotes for all keys/strings and no trailing commas. "
        "Estimate food type and nutrition for the portion shown. "
        "If unsure, use low confidence and add warnings; do NOT fabricate precise numbers."
    )
    user_prompt = (
        f"Locale: {locale_str}\n"
        "Task:\n"
        "1) Identify all foods in the photo.\n"
        "2) Estimate portion and grams.\n"
        "3) Estimate nutrition for the consumed portion: calories_kcal, protein_g, carbs_g, fat_g.\n"
        "4) If you can't identify any food, return items: [] and add a warning.\n"
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
        # Avoid inheriting the default agent prompt (e.g. clinical) which can break JSON-only output.
        "agent": cfg.agent,
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
                raise RuntimeError("OpenCode session id missing")

            msg_url = f"{session_url}/{session_id}/message"

            def post_message(msg_payload: Dict[str, Any]) -> object:
                resp = client.post(msg_url, headers=headers, json=msg_payload)
                content_type = (resp.headers.get("content-type") or "").lower()
                if resp.status_code >= 400:
                    resp.raise_for_status()
                if "text/html" in content_type:
                    raise RuntimeError("OpenCode API returned HTML")
                raw = resp.text or ""
                if not raw.strip():
                    raise RuntimeError(
                        "OpenCode message endpoint returned an empty body "
                        "(agent may be missing; restart opencode to reload .opencode/agents)."
                    )
                try:
                    return resp.json()
                except Exception as exc:
                    snippet = raw.replace("\n", " ").strip()[:200]
                    raise RuntimeError(f"OpenCode returned non-JSON response: {snippet}") from exc

            try:
                data = post_message(payload)
            except Exception as exc:
                last_error = exc
                # If a custom agent is misconfigured / not loaded (no file watcher), fall back to a built-in one.
                if payload.get("agent") and payload.get("agent") != "general":
                    payload2 = dict(payload)
                    payload2["agent"] = "general"
                    data = post_message(payload2)
                    last_error = None
                else:
                    raise
        except Exception as exc:
            last_error = exc

    if data is None:
        raise RuntimeError(f"OpenCode vision call failed: {last_error}")

    opencode_error = _extract_error_from_opencode_response(data)
    if opencode_error:
        raise RuntimeError(opencode_error)

    content = _extract_text_from_opencode_response(data)
    parsed: Dict[str, Any]
    try:
        parsed = _parse_model_output_json(content or "")
    except Exception as exc:
        # Don't fail the whole request when the model returns non-JSON (or empty) output.
        # The iOS review screen can still let users manually fill in food items.
        log.warning("diet vision output parse failed: %s", exc, exc_info=True)
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
