"""Text cleaning processor."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.ingestion.exceptions import ProcessorError
from app.ingestion.schemas import CleanedDocument, RawDocument

logger = logging.getLogger(__name__)

BOILERPLATE_KEYWORDS = {
    "navigation",
    "menu",
    "footer",
    "header",
    "cookie",
    "privacy",
    "terms",
    "sign in",
    "login",
    "subscribe",
}


class CleanerProcessor:
    """Cleans raw source content while preserving meaningful text."""

    def clean_document(self, document: RawDocument) -> CleanedDocument:
        """Convert a `RawDocument` into a cleaned, normalized document."""
        try:
            html_hint = str(document.metadata_json.get("raw_html") or document.raw_content)
            cleaned_text = self.clean_text(html_hint)
            if not cleaned_text:
                raise ProcessorError("cleaned content is empty")

            metadata = dict(document.metadata_json)
            metadata["cleaning_applied"] = True

            return CleanedDocument(
                document_id=document.document_id,
                cleaned_text=cleaned_text,
                language=str(metadata.get("language")) if metadata.get("language") else None,
                summary=str(metadata.get("summary")) if metadata.get("summary") else None,
                content_hash=self._stable_hash(cleaned_text),
                metadata_json=metadata,
            )
        except Exception as exc:
            logger.exception("clean_document_failed", exc_info=exc)
            if isinstance(exc, ProcessorError):
                raise
            raise ProcessorError("failed to clean document") from exc

    def clean_text(self, content: str) -> str:
        """Clean raw HTML/text input into normalized plain text."""
        if not content.strip():
            return ""

        text = self._remove_scripts_and_styles(content)
        text = self._strip_html_tags(text)
        text = self._remove_boilerplate_lines(text)
        text = self._normalize_whitespace(text)
        return text

    def _remove_scripts_and_styles(self, content: str) -> str:
        pattern = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", flags=re.IGNORECASE | re.DOTALL)
        return pattern.sub(" ", content)

    def _strip_html_tags(self, content: str) -> str:
        no_tags = re.sub(r"<[^>]+>", " ", content, flags=re.IGNORECASE)
        return no_tags

    def _remove_boilerplate_lines(self, content: str) -> str:
        lines = content.splitlines()
        filtered: list[str] = []
        for line in lines:
            normalized = line.strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if any(keyword in lowered for keyword in BOILERPLATE_KEYWORDS) and len(normalized) < 120:
                continue
            filtered.append(normalized)
        return "\n".join(filtered)

    def _normalize_whitespace(self, content: str) -> str:
        content = re.sub(r"[ \t\r\f\v]+", " ", content)
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = re.sub(r" +\n", "\n", content)
        return content.strip()

    def _stable_hash(self, text: str) -> str:
        import hashlib

        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def clean_text(content: str) -> str:
    """Backward-compatible helper used by earlier skeletons."""
    return CleanerProcessor().clean_text(content)
