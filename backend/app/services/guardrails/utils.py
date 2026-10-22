"""Deterministic text utility functions for guardrails modules."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# Arabic and Persian digit families mapped to ASCII for deterministic matching.
_DIGIT_TRANSLATION = str.maketrans(
    "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9"
    "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",
    "0123456789" * 2,
)

_PERSIAN_CHAR_TRANSLATION = str.maketrans(
    {
        "ك": "ک",
        "ي": "ی",
        "ى": "ی",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ۀ": "ه",
    }
)

_DIACRITICS_RE = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
_TOKEN_SPLIT_RE = re.compile(r"[^0-9a-zA-Z\u0600-\u06FF]+")
_NUMBER_RE = re.compile(r"[-+]?\d+(?:[.,/]\d+)?")
_CLAIM_SPLIT_RE = re.compile(r"[\n\r.!?؟؛;]+")


def normalize_text(text: str) -> str:
    """Normalize English/Persian text for deterministic matching."""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.translate(_DIGIT_TRANSLATION)
    normalized = normalized.translate(_PERSIAN_CHAR_TRANSLATION)
    normalized = normalized.replace("\u200c", " ")
    normalized = _DIACRITICS_RE.sub("", normalized)
    normalized = normalized.casefold()
    return " ".join(normalized.split())


def tokenize_text(text: str) -> set[str]:
    """Tokenize text into a deduplicated set of normalized tokens."""
    normalized = normalize_text(text)
    tokens = {
        token
        for token in _TOKEN_SPLIT_RE.split(normalized)
        if token and not token.isspace()
    }
    return tokens


def keyword_overlap_score(query: str, text: str) -> float:
    """Return the fraction of query tokens covered by text tokens."""
    query_tokens = tokenize_text(query)
    if not query_tokens:
        return 0.0

    text_tokens = tokenize_text(text)
    overlap = query_tokens & text_tokens
    return round(len(overlap) / len(query_tokens), 4)


def simple_text_similarity(a: str, b: str) -> float:
    """Compute a lightweight similarity score in [0.0, 1.0]."""
    norm_a = normalize_text(a)
    norm_b = normalize_text(b)

    if not norm_a and not norm_b:
        return 1.0
    if not norm_a or not norm_b:
        return 0.0

    token_a = tokenize_text(norm_a)
    token_b = tokenize_text(norm_b)
    union = token_a | token_b
    jaccard = len(token_a & token_b) / len(union) if union else 1.0

    sequence_ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
    return round((jaccard * 0.6) + (sequence_ratio * 0.4), 4)


def contains_any(text: str, patterns: list[str]) -> list[str]:
    """Return matched patterns found in text using normalized substring checks."""
    haystack = normalize_text(text)
    matched: list[str] = []

    for pattern in patterns:
        normalized_pattern = normalize_text(pattern)
        if normalized_pattern and normalized_pattern in haystack:
            matched.append(pattern)

    return matched


def extract_numbers(text: str) -> list[str]:
    """Extract integer/decimal-like number strings from Persian/English text."""
    normalized = normalize_text(text)
    return _NUMBER_RE.findall(normalized)


def split_into_claims(response: str) -> list[str]:
    """Split a response into short, deterministic claim chunks."""
    normalized = normalize_text(response)
    raw_parts = _CLAIM_SPLIT_RE.split(normalized)

    claims: list[str] = []
    for part in raw_parts:
        part = part.strip(" -\t")
        if not part:
            continue

        sub_parts = re.split(r"\s+(?:and|but|or|اما|ولی|یا)\s+", part)
        for sub_part in sub_parts:
            cleaned = sub_part.strip()
            if cleaned:
                claims.append(cleaned)

    return claims
