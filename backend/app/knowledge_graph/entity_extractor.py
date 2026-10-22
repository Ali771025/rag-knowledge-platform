"""Hybrid entity extraction (spaCy + Claude)."""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.claude_client import ClaudeClient, ClaudeClientAPIError, ClaudeClientConfigurationError
from app.ingestion.schemas import DocumentChunk
from app.knowledge_graph.schemas import EntityExtractionResult, GraphEntity

logger = logging.getLogger(__name__)

SPACY_ALLOWED_LABELS = {"ORG", "PERSON", "PRODUCT", "GPE", "WORK_OF_ART"}
ZERO_UUID = UUID("00000000-0000-0000-0000-000000000000")

SPACY_TYPE_MAP = {
    "ORG": "organization",
    "PERSON": "person",
    "PRODUCT": "technology",
    "GPE": "location",
    "WORK_OF_ART": "concept",
}

LLM_ALLOWED_TYPES = {
    "concept": "concept",
    "technology": "technology",
    "project": "technology",
    "feature": "concept",
    "service": "technology",
    "organization": "organization",
    "person": "person",
    "document": "concept",
}

TYPE_PRIORITY = {
    "technology": 5,
    "concept": 4,
    "organization": 3,
    "person": 3,
    "location": 2,
    "other": 1,
}


class EntityExtractor:
    """Extract candidate entities from text with robust fallbacks."""

    def __init__(self, claude_client: ClaudeClient | None = None, use_llm: bool | None = None) -> None:
        self.claude_client = claude_client or ClaudeClient()
        self.use_llm = settings.knowledge_graph_entity_llm_enabled if use_llm is None else use_llm
        self.spacy_model_name = os.getenv("SPACY_MODEL", "en_core_web_sm")
        self._spacy_nlp = None
        self._spacy_load_failed = False

    def extract_entities(self, text: str, metadata: dict | None = None) -> list[GraphEntity]:
        """Extract entities from text and optional metadata context."""
        content = text.strip()
        if not content:
            return []

        spacy_entities = self._extract_spacy_entities(content)
        llm_entities = self._extract_llm_entities(content, metadata or {})
        merged = self._merge_entities(spacy_entities, llm_entities)
        logger.info(
            "entity_extraction_completed",
            extra={"spacy_count": len(spacy_entities), "llm_count": len(llm_entities), "merged_count": len(merged)},
        )
        return merged

    def extract_from_chunks(self, chunks: list[DocumentChunk]) -> EntityExtractionResult:
        """Extract entities from a list of chunks and return merged result."""
        started = time.perf_counter()
        if not chunks:
            return EntityExtractionResult(
                document_id=ZERO_UUID,
                chunk_id=None,
                entities=[],
                model_name=self._result_model_name(),
                latency_ms=0,
                status="completed",
                errors=["no_chunks_provided"],
            )

        errors: list[str] = []
        merged: dict[str, GraphEntity] = {}

        for chunk in chunks:
            try:
                entities = self.extract_entities(chunk.text, metadata=dict(chunk.metadata_json or {}))
                for entity in entities:
                    key = self._normalize_name(entity.name)
                    if not key:
                        continue
                    existing = merged.get(key)
                    if existing is None or self._should_replace(existing, entity):
                        merged[key] = entity
                    elif entity.name not in existing.aliases and entity.name.lower() != existing.name.lower():
                        existing.aliases.append(entity.name)
            except Exception as exc:
                logger.warning("entity_extract_chunk_failed", extra={"chunk_id": str(chunk.chunk_id), "error": str(exc)})
                errors.append(f"chunk:{chunk.chunk_id}:{exc}")

        latency_ms = int((time.perf_counter() - started) * 1000)
        status = "completed" if not errors else ("failed" if not merged else "completed")
        return EntityExtractionResult(
            document_id=chunks[0].document_id,
            chunk_id=None,
            entities=list(merged.values()),
            model_name=self._result_model_name(),
            latency_ms=latency_ms,
            status=status,
            errors=errors,
        )

    async def extract(self, content: str) -> list[GraphEntity]:
        """Backward-compatible async wrapper."""
        return self.extract_entities(content)

    def _extract_spacy_entities(self, text: str) -> list[GraphEntity]:
        nlp = self._get_spacy_model()
        if nlp is None:
            return []
        entities: list[GraphEntity] = []
        try:
            doc = nlp(text)
            for item in doc.ents:
                if item.label_ not in SPACY_ALLOWED_LABELS:
                    continue
                name = self._sanitize_name(item.text)
                if not name:
                    continue
                entity_type = SPACY_TYPE_MAP.get(item.label_, "other")
                confidence = 0.65
                entities.append(
                    GraphEntity(
                        name=name,
                        entity_type=entity_type,  # type: ignore[arg-type]
                        confidence=confidence,
                        aliases=[],
                        metadata_json={"source": "spacy", "spacy_label": item.label_},
                    )
                )
        except Exception as exc:
            logger.warning("spacy_entity_extraction_failed", extra={"error": str(exc)})
            return []
        return entities

    def _extract_llm_entities(self, text: str, metadata: dict[str, Any]) -> list[GraphEntity]:
        if not self.use_llm:
            return []
        prompt = self._build_llm_prompt(text, metadata)
        system_prompt = (
            "Extract entities from text. Return JSON ONLY as an array with items: "
            "{\"name\":\"...\",\"type\":\"...\",\"properties\":{}}. "
            "Allowed types: Concept, Technology, Project, Feature, Service, Organization, Person, Document."
        )
        try:
            payload = self.claude_client.generate_json(prompt=prompt, system_prompt=system_prompt)
        except (ClaudeClientConfigurationError, ClaudeClientAPIError) as exc:
            logger.info("llm_entity_extraction_unavailable", extra={"error": str(exc)})
            return []
        except Exception as exc:
            logger.warning("llm_entity_extraction_failed", extra={"error": str(exc)})
            return []

        if not isinstance(payload, list):
            logger.warning("llm_entity_payload_invalid_type", extra={"type": type(payload).__name__})
            return []

        entities: list[GraphEntity] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            raw_name = item.get("name")
            raw_type = item.get("type")
            properties = item.get("properties", {})
            name = self._sanitize_name(str(raw_name) if raw_name is not None else "")
            mapped_type = self._map_llm_type(raw_type)
            if not name or mapped_type is None:
                continue
            if not isinstance(properties, dict):
                properties = {}
            entities.append(
                GraphEntity(
                    name=name,
                    entity_type=mapped_type,  # type: ignore[arg-type]
                    confidence=0.85,
                    aliases=[],
                    metadata_json={"source": "claude", "properties": properties},
                )
            )
        return entities

    def _build_llm_prompt(self, text: str, metadata: dict[str, Any]) -> str:
        snippet = text[:6000]
        meta_bits = {
            "source_type": metadata.get("source_type"),
            "title": metadata.get("title"),
            "topic": metadata.get("topic"),
            "category": metadata.get("category"),
        }
        return (
            "Identify important entities from this text.\n"
            f"Metadata: {meta_bits}\n"
            f"Text:\n{snippet}\n\n"
            "Return JSON only."
        )

    def _merge_entities(self, spacy_entities: list[GraphEntity], llm_entities: list[GraphEntity]) -> list[GraphEntity]:
        merged: dict[str, GraphEntity] = {}
        # Insert spaCy first, then let LLM replace richer types.
        for entity in spacy_entities + llm_entities:
            key = self._normalize_name(entity.name)
            if not key:
                continue
            existing = merged.get(key)
            if existing is None:
                merged[key] = entity
                continue
            if self._should_replace(existing, entity):
                aliases = self._merge_aliases(existing.aliases + [existing.name] + entity.aliases)
                entity.aliases = aliases
                merged[key] = entity
            else:
                existing.aliases = self._merge_aliases(existing.aliases + [entity.name] + entity.aliases)
        return list(merged.values())

    def _should_replace(self, current: GraphEntity, candidate: GraphEntity) -> bool:
        current_priority = TYPE_PRIORITY.get(current.entity_type, 0)
        candidate_priority = TYPE_PRIORITY.get(candidate.entity_type, 0)
        if candidate_priority != current_priority:
            return candidate_priority > current_priority
        return candidate.confidence > current.confidence

    def _normalize_name(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower())

    def _sanitize_name(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value.strip())
        cleaned = re.sub(r"^[\"'`\-:;,.\s]+|[\"'`\-:;,\s]+$", "", cleaned)
        return cleaned[:256]

    def _map_llm_type(self, raw_type: Any) -> str | None:
        if raw_type is None:
            return None
        lowered = str(raw_type).strip().lower()
        return LLM_ALLOWED_TYPES.get(lowered)

    def _merge_aliases(self, aliases: list[str]) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        for alias in aliases:
            cleaned = self._sanitize_name(alias)
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            output.append(cleaned)
        return output[:20]

    def _get_spacy_model(self):
        if self._spacy_load_failed:
            return None
        if self._spacy_nlp is not None:
            return self._spacy_nlp
        try:
            import spacy

            self._spacy_nlp = spacy.load(self.spacy_model_name)
            return self._spacy_nlp
        except Exception as exc:
            self._spacy_load_failed = True
            logger.info("spacy_model_unavailable", extra={"model": self.spacy_model_name, "error": str(exc)})
            return None

    def _result_model_name(self) -> str:
        if self.use_llm:
            return f"{self.spacy_model_name}+{self.claude_client.model}"
        return self.spacy_model_name
