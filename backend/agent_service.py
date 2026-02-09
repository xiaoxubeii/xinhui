# -*- coding: utf-8 -*-
"""Unified agent calling service (Qwen-compatible + optional RAG).

Both the legacy `/api/agent/ask` endpoint and the new chat endpoint reuse this module.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from fastapi import HTTPException

from .config import settings

# ---------- Agent config (OpenCode JSONC) ----------

_agent_config_cache: Dict[str, Any] = {"mtime": None, "config": None}


def _strip_jsonc(text: str) -> str:
    # Remove // and /* */ comments (best-effort).
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\\*.*?\\*/", "", text, flags=re.DOTALL)
    return text


def _replace_vars(text: str, base_dir: Path) -> str:
    def repl_env(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return os.environ.get(key, "")

    def repl_file(match: re.Match[str]) -> str:
        raw_path = match.group(1).strip()
        file_path = Path(raw_path)
        if not file_path.is_absolute():
            file_path = base_dir / file_path
        try:
            return file_path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    text = re.sub(r"\{env:([^}]+)\}", repl_env, text)
    text = re.sub(r"\{file:([^}]+)\}", repl_file, text)
    return text


def _substitute_vars(value: Any, base_dir: Path) -> Any:
    if isinstance(value, str):
        return _replace_vars(value, base_dir)
    if isinstance(value, list):
        return [_substitute_vars(v, base_dir) for v in value]
    if isinstance(value, dict):
        return {k: _substitute_vars(v, base_dir) for k, v in value.items()}
    return value


def _load_agent_config() -> Optional[Dict[str, Any]]:
    config_path = settings.agent_config_path
    if not config_path or not config_path.exists():
        return None
    mtime = config_path.stat().st_mtime
    if _agent_config_cache["config"] is not None and _agent_config_cache["mtime"] == mtime:
        return _agent_config_cache["config"]
    raw = config_path.read_text(encoding="utf-8")
    parsed = json.loads(_strip_jsonc(raw))
    parsed = _substitute_vars(parsed, config_path.parent)
    _agent_config_cache["mtime"] = mtime
    _agent_config_cache["config"] = parsed
    return parsed


def resolve_agent_settings() -> Dict[str, Any]:
    config = _load_agent_config()
    if config:
        model_full = config.get("model") or config.get("agent", {}).get("model")
        if not model_full:
            raise HTTPException(status_code=500, detail="Agent model missing in config.")
        provider_map = config.get("provider") or config.get("providers") or {}
        if "/" in model_full:
            provider_id, model_name = model_full.split("/", 1)
        else:
            fallback_provider = (
                config.get("default_provider")
                or config.get("provider_id")
                or (list(provider_map.keys())[0] if len(provider_map) == 1 else None)
            )
            provider_id, model_name = fallback_provider, model_full
        if not provider_id:
            raise HTTPException(status_code=500, detail="Agent provider missing in config.")
        provider_conf = provider_map.get(provider_id, {})
        options = provider_conf.get("options", {}) if isinstance(provider_conf, dict) else {}
        base_url = options.get("baseURL") or options.get("baseUrl") or options.get("endpoint")
        api_key = options.get("apiKey") or options.get("api_key") or options.get("apikey")
        timeout = options.get("timeout") or settings.qwen_timeout
        temperature = config.get("agent", {}).get("temperature", settings.qwen_temperature)
        max_tokens = config.get("agent", {}).get("max_tokens", settings.qwen_max_tokens)
        system_prompt = config.get("agent", {}).get("system_prompt")

        if not base_url:
            raise HTTPException(status_code=500, detail="Agent baseURL missing in config.")
        if not api_key:
            raise HTTPException(status_code=500, detail="Agent apiKey missing in config.")

        return {
            "provider": provider_id,
            "model": model_name,
            "base_url": base_url,
            "api_key": api_key,
            "timeout": float(timeout),
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "system_prompt": system_prompt,
        }

    # Fallback to legacy Qwen env settings.
    if not settings.qwen_api_key:
        raise HTTPException(status_code=500, detail="QWEN_API_KEY not set")
    return {
        "provider": "qwen",
        "model": settings.qwen_model,
        "base_url": settings.qwen_base_url,
        "api_key": settings.qwen_api_key,
        "timeout": settings.qwen_timeout,
        "temperature": settings.qwen_temperature,
        "max_tokens": settings.qwen_max_tokens,
        "system_prompt": None,
    }


def call_agent(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    cfg = resolve_agent_settings()
    base_url = cfg["base_url"].rstrip("/")
    if base_url.endswith("/chat/completions"):
        url = base_url
    else:
        url = f"{base_url}/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=cfg["timeout"]) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Agent API error: {exc}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Agent API unreachable: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent API failure: {exc}") from exc


# ---------- RAG ----------

_retriever_instance = None


def _get_retriever():
    global _retriever_instance
    if _retriever_instance is None:
        try:
            from .rag import KnowledgeRetriever

            db_path = settings.data_root / "vector_db"
            if db_path.exists():
                _retriever_instance = KnowledgeRetriever(db_path)
        except ImportError:
            pass
    return _retriever_instance


def retrieve_context(question: str, top_k: int = 3) -> str:
    retriever = _get_retriever()
    if retriever and retriever.is_ready():
        return retriever.retrieve_with_context(question, top_k=top_k, max_context_length=1500)
    return ""


def ask_agent(
    *,
    question: str,
    context: Dict[str, Any],
    history: List[Dict[str, str]] | None = None,
) -> Dict[str, str]:
    cfg = resolve_agent_settings()
    system_prompt = cfg.get("system_prompt") or (
        "You are a clinical CPET assistant. Answer strictly based on the provided JSON context. "
        "If the answer is not in the context, say you do not know. "
        "Be concise, professional, and avoid making definitive diagnoses."
    )
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    history = history or []
    for msg in history[-6:]:
        role = msg.get("role")
        content = msg.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            messages.append({"role": role, "content": content})

    rag_context = retrieve_context(question)
    context_str = json.dumps(context, ensure_ascii=False)
    if rag_context:
        user_content = f"参考知识:\n{rag_context}\n\nContext (JSON):\n{context_str}\n\nQuestion:\n{question}"
    else:
        user_content = f"Context (JSON):\n{context_str}\n\nQuestion:\n{question}"
    messages.append({"role": "user", "content": user_content})

    result = call_agent(messages)
    answer = (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    return {"answer": answer or "暂无可用回答。", "model": cfg["model"]}

