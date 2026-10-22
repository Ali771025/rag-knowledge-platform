"""Base source loader interfaces and shared helpers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.ingestion.exceptions import IngestionValidationError, SourceLoadError
from app.ingestion.schemas import RawDocument, SourceConfig

logger = logging.getLogger(__name__)


class BaseSourceLoader(ABC):
    """Abstract source loader contract for ingestion inputs.

    Concrete implementations (web, discord, file, docs) should validate source
    configuration and return normalized `RawDocument` records.
    """

    @abstractmethod
    async def load(self, config: SourceConfig) -> list[RawDocument]:
        """Load raw documents from a configured source."""

    def validate_source(self, config: SourceConfig) -> None:
        """Validate generic source configuration before loading."""
        if not config.source_uri.strip():
            raise IngestionValidationError("source_uri must not be empty")
        if config.max_items <= 0:
            raise IngestionValidationError("max_items must be greater than zero")
        if config.timeout_seconds <= 0:
            raise IngestionValidationError("timeout_seconds must be greater than zero")
        logger.debug(
            "source_config_validated",
            extra={"source_type": config.source_type, "source_uri": config.source_uri},
        )

    def normalize_metadata(self, metadata: dict[str, Any] | None) -> dict[str, Any]:
        """Normalize metadata payload into JSON-safe dictionary."""
        if metadata is None:
            return {}
        normalized: dict[str, Any] = {}
        for key, value in metadata.items():
            normalized[str(key)] = value
        return normalized

    def build_raw_document(
        self,
        *,
        config: SourceConfig,
        raw_content: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        document_id: UUID | None = None,
    ) -> RawDocument:
        """Build a validated `RawDocument` from extracted source payload."""
        content = raw_content.strip()
        if not content:
            raise SourceLoadError("raw_content is empty after normalization")
        source_context = self._extract_source_context(config)
        metadata_payload = self.normalize_metadata(metadata)
        if source_context:
            metadata_payload = {**source_context, **metadata_payload}
        payload: dict[str, Any] = {
            "source_type": config.source_type,
            "source_uri": config.source_uri,
            "title": title.strip() if title else None,
            "raw_content": content,
            "metadata_json": metadata_payload,
        }
        if document_id is not None:
            payload["document_id"] = document_id
        return RawDocument(**payload)

    def _extract_source_context(self, config: SourceConfig) -> dict[str, Any]:
        options = dict(config.options or {})
        context: dict[str, Any] = {}
        for key in ("knowledge_source_id", "domain", "label"):
            value = options.get(key)
            if value is None:
                continue
            context[key] = value

        tags_value = options.get("tags")
        if isinstance(tags_value, list):
            context["tags"] = [str(item).strip() for item in tags_value if str(item).strip()]
        return context
