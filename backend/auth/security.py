# -*- coding: utf-8 -*-
"""Auth — password hashing + JWT + FastAPI helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import Depends, HTTPException, Request

from ..config import settings
from .storage import get_user_by_id
from ..api_keys.storage import lookup_api_key

TOKEN_COOKIE_NAME = "xinhui_token"

# Password hashing (stdlib pbkdf2_hmac).
_PBKDF2_ALG = "sha256"
_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac(_PBKDF2_ALG, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    dk_b64 = base64.urlsafe_b64encode(dk).decode("ascii").rstrip("=")
    return f"pbkdf2_{_PBKDF2_ALG}${_PBKDF2_ITERATIONS}${salt_b64}${dk_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iter_s, salt_b64, dk_b64 = password_hash.split("$", 3)
        if not scheme.startswith("pbkdf2_"):
            return False
        alg = scheme.split("_", 1)[1]
        iterations = int(iter_s)
        salt = _b64url_decode(salt_b64)
        expected = _b64url_decode(dk_b64)
        actual = hashlib.pbkdf2_hmac(alg, password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(*, user_id: str, email: str) -> str:
    now = _utc_now()
    exp = now + timedelta(days=int(settings.token_ttl_days))
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return _jwt_encode(payload, settings.jwt_secret)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = _jwt_decode(token, settings.jwt_secret)
        exp = int(payload.get("exp") or 0)
        if exp and exp < int(_utc_now().timestamp()):
            raise HTTPException(status_code=401, detail="Token expired")
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


def _jwt_encode(payload: Dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _jwt_decode(token: str, secret: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid token")
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("bad signature")
    payload_raw = _b64url_decode(payload_b64)
    payload = json.loads(payload_raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("bad payload")
    return payload


def get_token_from_request(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        return token or None
    cookie = request.cookies.get(TOKEN_COOKIE_NAME)
    return cookie or None


def get_current_user_from_request(request: Request) -> Dict[str, Any]:
    # If middleware already authenticated, reuse it.
    user = getattr(request.state, "user", None)
    if user:
        return user

    api_key = get_api_key_from_request(request)
    if api_key:
        found = lookup_api_key(api_key)
        if not found:
            raise HTTPException(status_code=401, detail="Invalid API key")
        user_row, api_key_id = found
        request.state.user = user_row
        request.state.api_key_id = api_key_id
        return user_row

    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    user_id = str(payload.get("sub") or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_row = get_user_by_id(user_id)
    if not user_row:
        raise HTTPException(status_code=401, detail="User not found")

    # Cache on request for downstream handlers.
    request.state.user = user_row
    return user_row


def get_current_user(user: Dict[str, Any] = Depends(get_current_user_from_request)) -> Dict[str, Any]:
    return user


def get_api_key_from_request(request: Request) -> Optional[str]:
    # Prefer explicit API key header to avoid JWT confusion.
    header = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if header and header.strip():
        return header.strip()
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("api-key "):
        token = auth.split(" ", 1)[1].strip()
        return token or None
    if auth.lower().startswith("apikey "):
        token = auth.split(" ", 1)[1].strip()
        return token or None
    return None
