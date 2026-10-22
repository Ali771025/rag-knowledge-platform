"""Metadata extraction processor."""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.claude_client import ClaudeClient, ClaudeClientAPIError, ClaudeClientConfigurationError
from app.ingestion.schemas import CleanedDocument

logger = logging.getLogger(__name__)

SECTION_TYPES = {"explanation", "faq", "tutorial", "concept", "announcement", "reference"}


class MetadataExtractorProcessor:
    """Extracts structured metadata using heuristic + optional LLM augmentation."""

    def __init__(self, claude_client: ClaudeClient | None = None, use_llm: bool | None = None) -> None:
        self.claude_client = claude_client or ClaudeClient()
        self.use_llm = settings.ingestion_metadata_llm_enabled if use_llm is None else use_llm

    def extract(self, document: CleanedDocument) -> dict[str, Any]:
        """Extract metadata from a cleaned document."""
        heuristic = self._heuristic_extract(document)
        if not self.use_llm:
            return heuristic

        try:
            llm_data = self._llm_extract(document)
            merged = self._merge_metadata(heuristic, llm_data)
            return self._normalize_metadata(merged)
        except (ClaudeClientConfigurationError, ClaudeClientAPIError, ValueError, TypeError) as exc:
            logger.warning("metadata_extractor_llm_fallback", extra={"document_id": str(document.document_id), "error": str(exc)})
            return heuristic
        except Exception as exc:
            logger.exception("metadata_extractor_unexpected_llm_failure", exc_info=exc)
            return heuristic

    def extract_batch(self, documents: list[CleanedDocument]) -> list[dict[str, Any]]:
        """Extract metadata for a list of cleaned documents."""
        results: list[dict[str, Any]] = []
        for document in documents:
            results.append(self.extract(document))
        return results

    def _heuristic_extract(self, document: CleanedDocument) -> dict[str, Any]:
        text = document.cleaned_text
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        heading = self._extract_heading(lines)
        language = document.language or "und"
        word_count = self._count_words(text)
        tags = self._extract_tags(text)
        section_type = self._infer_section_type(text, heading)
        topic, category, subcategory = self._infer_topic_category(heading, text)
        difficulty = self._infer_difficulty(word_count, text)
        related_topics = self._extract_related_topics(text, topic)
        parent_topic = self._infer_parent_topic(category, topic)

        return self._normalize_metadata(
            {
                "topic": topic,
                "category": category,
                "subcategory": subcategory,
                "difficulty_level": difficulty,
                "tags": tags,
                "language": language,
                "word_count": word_count,
                "heading": heading,
                "section_type": section_type,
                "parent_topic": parent_topic,
                "related_topics": related_topics,
            }
        )

    def _llm_extract(self, document: CleanedDocument) -> dict[str, Any]:
        prompt = self._build_llm_prompt(document)
        system_prompt = (
            "You are a metadata classifier. "
            "Return ONLY strict JSON object with keys: "
            "topic, category, subcategory, difficulty_level, tags, language, word_count, "
            "heading, section_type, parent_topic, related_topics. No prose."
        )
        payload = self.claude_client.generate_json(prompt=prompt, system_prompt=system_prompt)
        if not isinstance(payload, dict):
            raise ValueError("LLM metadata response must be a JSON object")
        return payload

    def _build_llm_prompt(self, document: CleanedDocument) -> str:
        snippet = document.cleaned_text[:6000]
        return (
            "Extract structured metadata from the following content.\n\n"
            f"Document ID: {document.document_id}\n"
            f"Detected language: {document.language or 'unknown'}\n"
            "Content:\n"
            f"{snippet}\n\n"
            "Return valid JSON only."
        )

    def _merge_metadata(self, baseline: dict[str, Any], llm_data: dict[str, Any]) -> dict[str, Any]:
        merged = dict(baseline)
        for key, value in llm_data.items():
            if value in (None, "", [], {}):
                continue
            merged[key] = value
        return merged

    def _normalize_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        topic = self._safe_str(data.get("topic"))
        category = self._safe_str(data.get("category"))
        subcategory = self._safe_str(data.get("subcategory"))
        difficulty = self._clamp_int(data.get("difficulty_level"), minimum=1, maximum=5, default=2)
        tags = self._normalize_string_list(data.get("tags"))
        language = self._normalize_language(data.get("language"))
        word_count = self._clamp_int(data.get("word_count"), minimum=0, maximum=2_000_000, default=0)
        heading = self._safe_str(data.get("heading"))
        section_type = self._normalize_section_type(data.get("section_type"))
        parent_topic = self._safe_str(data.get("parent_topic"))
        related_topics = self._normalize_string_list(data.get("related_topics"))

        return {
            "topic": topic,
            "category": category,
            "subcategory": subcategory,
            "difficulty_level": difficulty,
            "tags": tags,
            "language": language,
            "word_count": word_count,
            "heading": heading,
            "section_type": section_type,
            "parent_topic": parent_topic,
            "related_topics": related_topics,
        }

    def _extract_heading(self, lines: list[str]) -> str:
        for line in lines:
            if re.match(r"^#{1,6}\s+.+", line):
                return re.sub(r"^#{1,6}\s+", "", line).strip()
        for line in lines:
            if len(line) <= 120:
                return line
        return "Untitled"

    def _count_words(self, text: str) -> int:
        return len(re.findall(r"\b[\w'-]+\b", text))

    def _extract_tags(self, text: str) -> list[str]:
        lowered = text.lower()
        candidates = [
            "api",
            "authentication",
            "authorization",
            "database",
            "sql",
            "python",
            "fastapi",
            "docker",
            "deployment",
            "security",
            "monitoring",
            "testing",
            "tutorial",
            "faq",
        ]
        tags = [item for item in candidates if re.search(rf"\b{re.escape(item)}\b", lowered)]
        return sorted(set(tags))[:20]

    def _infer_section_type(self, text: str, heading: str) -> str:
        lowered = f"{heading}\n{text[:1500]}".lower()
        if "faq" in lowered or re.search(r"\bq:\s|\bquestion\b", lowered):
            return "faq"
        if "tutorial" in lowered or "step " in lowered or "how to" in lowered:
            return "tutorial"
        if "announcement" in lowered or "release note" in lowered or "we are excited" in lowered:
            return "announcement"
        if "reference" in lowered or "api reference" in lowered:
            return "reference"
        if "concept" in lowered or "definition" in lowered:
            return "concept"
        return "explanation"

    def _infer_topic_category(self, heading: str, text: str) -> tuple[str, str, str]:
        heading_clean = heading.strip() or "General"
        first_words = re.findall(r"[A-Za-z0-9_-]+", heading_clean)
        topic = " ".join(first_words[:6]) if first_words else "General"

        lowered = text.lower()
        if any(token in lowered for token in ("sql", "database", "postgres", "query")):
            category = "data"
            subcategory = "database"
        elif any(token in lowered for token in ("api", "endpoint", "request", "response", "http")):
            category = "backend"
            subcategory = "api"
        elif any(token in lowered for token in ("deploy", "docker", "kubernetes", "infra")):
            category = "operations"
            subcategory = "deployment"
        else:
            category = "general"
            subcategory = "overview"
        return topic, category, subcategory

    def _infer_difficulty(self, word_count: int, text: str) -> int:
        score = 1
        if word_count > 300:
            score += 1
        if word_count > 800:
            score += 1
        if re.search(r"\b(architecture|optimization|concurrency|distributed|consistency)\b", text.lower()):
            score += 1
        if re.search(r"\b(proof|formal|theorem|complexity)\b", text.lower()):
            score += 1
        return max(1, min(score, 5))

    def _extract_related_topics(self, text: str, topic: str) -> list[str]:
        # Lightweight heuristic based on repeated capitalized terms.
        candidates = re.findall(r"\b[A-Z][a-zA-Z0-9_-]{2,}\b", text[:5000])
        normalized = [item.strip() for item in candidates if item.lower() != topic.lower()]
        unique: list[str] = []
        seen: set[str] = set()
        for item in normalized:
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            unique.append(item)
            if len(unique) >= 10:
                break
        return unique

    def _infer_parent_topic(self, category: str, topic: str) -> str:
        if category == "general":
            return "Knowledge Base"
        if topic and category not in topic.lower():
            return category.title()
        return "Knowledge Base"

    def _safe_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _normalize_string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = [item.strip() for item in re.split(r"[,\n;|]", value) if item.strip()]
            return self._unique(parts)
        if isinstance(value, list):
            parts = [str(item).strip() for item in value if str(item).strip()]
            return self._unique(parts)
        return []

    def _unique(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for item in items:
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            output.append(item)
        return output

    def _normalize_language(self, value: Any) -> str:
        language = self._safe_str(value).lower()
        if not language:
            return "und"
        return language[:16]

    def _normalize_section_type(self, value: Any) -> str:
        section_type = self._safe_str(value).lower()
        if section_type not in SECTION_TYPES:
            return "explanation"
        return section_type

    def _clamp_int(self, value: Any, minimum: int, maximum: int, default: int) -> int:
        try:
            number = int(value)
        except Exception:
            return default
        return max(minimum, min(number, maximum))


def extract_metadata(content: str) -> dict[str, Any]:
    """Backward-compatible helper used by earlier skeletons."""
    pseudo_document = CleanedDocument(
        document_id=UUID("00000000-0000-0000-0000-000000000000"),
        cleaned_text=content if content.strip() else "empty",
        content_hash="0" * 64,
        metadata_json={},
    )
    return MetadataExtractorProcessor(use_llm=False).extract(pseudo_document)
