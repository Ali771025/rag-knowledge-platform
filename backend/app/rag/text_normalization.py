"""Unicode-aware text normalization shared by retrieval and grounding."""

from __future__ import annotations

import re
import unicodedata

_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
        "ۀ": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
    }
)
_DIACRITICS = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
_TOKEN_PATTERN = re.compile(r"[^\W_]+(?:[._+/\-][^\W_]+)*", flags=re.UNICODE)


def normalize_text(value: str) -> str:
    """Normalize Persian/Arabic variants and spacing without translating text."""
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    normalized = normalized.translate(_ARABIC_TO_PERSIAN)
    normalized = _DIACRITICS.sub("", normalized)
    return " ".join(normalized.casefold().split())


def tokenize(value: str, *, min_length: int = 2) -> list[str]:
    """Return ordered Unicode word tokens suitable for Persian and Latin text."""
    normalized = normalize_text(value)
    return [token for token in _TOKEN_PATTERN.findall(normalized) if len(token) >= min_length]


def unique_tokens(value: str, *, stopwords: set[str] | None = None, limit: int = 24) -> list[str]:
    """Return normalized, de-duplicated tokens while preserving query order."""
    excluded = stopwords or set()
    output: list[str] = []
    seen: set[str] = set()
    for token in tokenize(value):
        if token in excluded or token in seen:
            continue
        seen.add(token)
        output.append(token)
        if len(output) >= limit:
            break
    return output


def contains_non_latin_letters(value: str) -> bool:
    """Detect queries that need Unicode-aware lexical support."""
    return any(char.isalpha() and not ("a" <= char.casefold() <= "z") for char in value)
