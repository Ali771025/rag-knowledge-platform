from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "private_key", "seed", "mnemonic"}
_PATTERNS = (
    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"), "[MASKED_EMAIL]"),
    (re.compile(r"(?<!\d)(?:\+?98|0)?9\d{9}(?!\d)"), "[MASKED_PHONE]"),
    (re.compile(r"\b0x[a-fA-F0-9]{40}\b"), "[MASKED_WALLET]"),
    (re.compile(r"\b(?:sk|pk)_[A-Za-z0-9_-]{16,}\b"), "[MASKED_TOKEN]"),
)


def mask_text(value: str | None) -> str | None:
    if value is None:
        return None
    masked = value
    for pattern, replacement in _PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked


def mask_sensitive(value: Any, *, key: str | None = None) -> Any:
    if key and key.lower() in _SENSITIVE_KEYS:
        return "[MASKED]"
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, dict):
        return {str(item_key): mask_sensitive(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return [mask_sensitive(item) for item in value]
    return value

