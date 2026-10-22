"""Language detection processor."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class LanguageDetectorProcessor:
    """Detects language using library-first strategy with heuristic fallback."""

    def detect_language(self, content: str) -> str:
        """Return ISO-like language code (e.g., en, es, fr)."""
        text = content.strip()
        if not text:
            return "und"

        language = self._detect_with_library(text)
        if language:
            return language
        return self._detect_with_heuristic(text)

    def _detect_with_library(self, text: str) -> str | None:
        """Try language detection with optional external libraries."""
        try:
            from langdetect import detect

            detected = detect(text)
            if detected:
                logger.debug("language_detected_langdetect", extra={"language": detected})
                return detected.lower()
        except Exception:
            pass

        try:
            from langid.langid import LanguageIdentifier, model

            identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)
            detected, _score = identifier.classify(text)
            if detected:
                logger.debug("language_detected_langid", extra={"language": detected})
                return detected.lower()
        except Exception:
            pass
        return None

    def _detect_with_heuristic(self, text: str) -> str:
        """Fallback heuristic language detection when libs are unavailable."""
        lowered = text.lower()
        # Very light-weight heuristics for robust fallback.
        spanish_markers = {" el ", " la ", " que ", " de ", " y ", " los ", " una "}
        french_markers = {" le ", " la ", " les ", " des ", " et ", " une ", " est "}
        german_markers = {" der ", " die ", " das ", " und ", " ist ", " nicht "}

        scored = {
            "es": sum(marker in lowered for marker in spanish_markers),
            "fr": sum(marker in lowered for marker in french_markers),
            "de": sum(marker in lowered for marker in german_markers),
            "en": 0,
        }
        ascii_ratio = self._ascii_ratio(text)
        if ascii_ratio > 0.92:
            scored["en"] += 1
        if re.search(r"\b(the|and|is|are|to|of|in)\b", lowered):
            scored["en"] += 2

        language = max(scored, key=scored.get)
        if scored[language] <= 0:
            return "und"
        return language

    def _ascii_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        ascii_count = sum(1 for char in text if ord(char) < 128)
        return ascii_count / len(text)


def detect_language(content: str) -> str:
    """Backward-compatible helper used by earlier skeletons."""
    return LanguageDetectorProcessor().detect_language(content)
