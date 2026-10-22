"""Deduplication processor."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _ItemFingerprint:
    """Internal item fingerprint used for near-duplicate checks."""

    hash_value: str
    tokens: set[str]


class DeduplicatorProcessor:
    """Deduplicates exact and near-exact repeated text entries."""

    def __init__(self, near_duplicate_threshold: float = 0.92) -> None:
        self.near_duplicate_threshold = near_duplicate_threshold
        self._known_hashes: set[str] = set()
        self._known_fingerprints: list[_ItemFingerprint] = []

    def hash_text(self, text: str) -> str:
        """Generate stable content hash for input text."""
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()

    def is_duplicate(self, hash_value: str) -> bool:
        """Check whether exact hash has already been observed."""
        return hash_value in self._known_hashes

    def filter_duplicates(self, items: list[Any]) -> list[Any]:
        """Filter exact and near-duplicate items, preserving order.

        Supports items as raw strings or objects containing text under:
        - attribute `raw_content` / `cleaned_text` / `text`
        - dict key `raw_content` / `cleaned_text` / `text`
        """
        output: list[Any] = []
        for item in items:
            text = self._extract_text(item)
            if not text:
                continue
            hash_value = self.hash_text(text)
            if self.is_duplicate(hash_value):
                logger.debug("deduplicator_exact_duplicate", extra={"hash": hash_value})
                continue

            current_tokens = self._tokenize(text)
            if self._is_near_duplicate(current_tokens):
                logger.debug("deduplicator_near_duplicate", extra={"hash": hash_value})
                continue

            self._known_hashes.add(hash_value)
            self._known_fingerprints.append(_ItemFingerprint(hash_value=hash_value, tokens=current_tokens))
            output.append(item)
        return output

    def _is_near_duplicate(self, tokens: set[str]) -> bool:
        if not tokens:
            return False
        for fingerprint in self._known_fingerprints:
            similarity = self._jaccard_similarity(tokens, fingerprint.tokens)
            if similarity >= self.near_duplicate_threshold:
                return True
        return False

    def _jaccard_similarity(self, left: set[str], right: set[str]) -> float:
        if not left and not right:
            return 1.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)

    def _normalize_text(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return normalized

    def _tokenize(self, text: str) -> set[str]:
        normalized = self._normalize_text(text)
        return set(token for token in re.split(r"[^a-z0-9]+", normalized) if token)

    def _extract_text(self, item: Any) -> str:
        if isinstance(item, str):
            return item
        for field in ("raw_content", "cleaned_text", "text", "content"):
            value = getattr(item, field, None)
            if isinstance(value, str) and value.strip():
                return value
        if isinstance(item, dict):
            for field in ("raw_content", "cleaned_text", "text", "content"):
                value = item.get(field)
                if isinstance(value, str) and value.strip():
                    return value
        return ""


def hash_text(text: str) -> str:
    """Module-level convenience wrapper for hashing text."""
    return DeduplicatorProcessor().hash_text(text)


def is_duplicate(hash_value: str) -> bool:
    """Module-level convenience wrapper (stateless default)."""
    return DeduplicatorProcessor().is_duplicate(hash_value)


def filter_duplicates(items: list[Any]) -> list[Any]:
    """Module-level convenience wrapper for duplicate filtering."""
    return DeduplicatorProcessor().filter_duplicates(items)


def deduplicate_chunks(chunks: list[str]) -> list[str]:
    """Backward-compatible helper used by earlier skeletons."""
    return filter_duplicates(chunks)
