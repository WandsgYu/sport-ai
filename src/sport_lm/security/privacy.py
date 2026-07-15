from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from typing import Any


_PRIVATE_KEYS = {
    "address",
    "api_key",
    "arguments",
    "authorization",
    "channel_user_id",
    "contact",
    "content",
    "credential",
    "email",
    "frame",
    "identity_ref",
    "ip",
    "message",
    "name",
    "password",
    "phone",
    "reply",
    "result",
    "secret",
    "text",
    "token",
    "tool_calls",
    "user_info",
    "wecom_id",
}

_PROCESS_SALT = os.urandom(32)

_PATTERNS = [
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"https?://[^\s]+", re.I),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?<!\d)\d{8,}(?!\d)"),
]


def pseudonymize(value: Any) -> str:
    """Return a stable, non-reversible reference suitable for local logs."""

    raw = str(value or "").encode("utf-8")
    if not raw:
        return "anonymous"
    digest = hmac.new(_PROCESS_SALT, raw, hashlib.sha256).hexdigest()
    return f"subject-{digest[:12]}"


def redact_text(value: Any) -> str:
    text = str(value or "")
    for pattern in _PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def sanitize(value: Any, key: str | None = None) -> Any:
    """Recursively sanitize a value before it is written to logs or UI."""

    normalized_key = (key or "").lower()
    if normalized_key in _PRIVATE_KEYS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def safe_json(value: Any) -> str:
    return json.dumps(sanitize(value), ensure_ascii=False, default=str)
