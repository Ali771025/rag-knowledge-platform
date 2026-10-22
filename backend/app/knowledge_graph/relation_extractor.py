"""Hybrid relation extraction (Claude + regex fallback)."""

from __future__ import annotations

import logging
import re
import time
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.claude_client import ClaudeClient, ClaudeClientAPIError, ClaudeClientConfigurationError
from app.ingestion.schemas import DocumentChunk
from app.knowledge_graph.schemas import GraphEntity, GraphRelation, RelationExtractionResult

logger = logging.getLogger(__name__)

ZERO_UUID = UUID("00000000-0000-0000-0000-000000000000")
ALLOWED_RELATIONS = {"USES", "DEPENDS_ON", "PART_OF", "IMPLEMENTS", "RELATED_TO", "PROVIDES", "MENTIONS"}

REGEX_RULES: list[tuple[str, str]] = [
    (r"\b(?P<source>[A-Za-z0-9 _\-]{2,80})\s+uses\s+(?P<target>[A-Za-z0-9 _\-]{2,80})\b", "USES"),
    (r"\b(?P<source>[A-Za-z0-9 _\-]{2,80})\s+depends on\s+(?P<target>[A-Za-z0-9 _\-]{2,80})\b", "DEPENDS_ON"),
    (r"\b(?P<source>[A-Za-z0-9 _\-]{2,80})\s+is part of\s+(?P<target>[A-Za-z0-9 _\-]{2,80})\b", "PART_OF"),
    (r"\b(?P<source>[A-Za-z0-9 _\-]{2,80})\s+implements\s+(?P<target>[A-Za-z0-9 _\-]{2,80})\b", "IMPLEMENTS"),
    (r"\b(?P<source>[A-Za-z0-9 _\-]{2,80})\s+provides\s+(?P<target>[A-Za-z0-9 _\-]{2,80})\b", "PROVIDES"),
]


class RelationExtractor:
    """Extract relations from text with LLM-first and regex fallback strategy."""

    def __init__(self, claude_client: ClaudeClient | None = None, use_llm: bool | None = None) -> None:
        self.claude_client = claude_client or ClaudeClient()
        self.use_llm = settings.knowledge_graph_relation_llm_enabled if use_llm is None else use_llm

    def extract_relations(self, text: str, entities: list[GraphEntity]) -> list[GraphRelation]:
        """Extract relations from a text block and known entities."""
        content = text.strip()
        if not content:
            return []

        entity_index = self._build_entity_index(entities)
        llm_relations = self._extract_llm_relations(content, entities, entity_index)
        regex_relations = self._extract_regex_relations(content, entity_index)
        merged = self._merge_relations(llm_relations, regex_relations)
        logger.info(
            "relation_extraction_completed",
            extra={"llm_count": len(llm_relations), "regex_count": len(regex_relations), "merged_count": len(merged)},
        )
        return merged

    def extract_from_chunks(self, chunks: list[DocumentChunk], entities: list[GraphEntity]) -> RelationExtractionResult:
        """Extract relations from chunks and return merged extraction result."""
        started = time.perf_counter()
        if not chunks:
            return RelationExtractionResult(
                document_id=ZERO_UUID,
                chunk_id=None,
                relations=[],
                model_name=self._result_model_name(),
                latency_ms=0,
                status="completed",
                errors=["no_chunks_provided"],
            )

        errors: list[str] = []
        merged: dict[str, GraphRelation] = {}
        for chunk in chunks:
            try:
                relations = self.extract_relations(chunk.text, entities)
                for relation in relations:
                    key = self._relation_key(relation)
                    existing = merged.get(key)
                    if existing is None or relation.confidence > existing.confidence:
                        merged[key] = relation
            except Exception as exc:
                logger.warning("relation_extract_chunk_failed", extra={"chunk_id": str(chunk.chunk_id), "error": str(exc)})
                errors.append(f"chunk:{chunk.chunk_id}:{exc}")

        latency_ms = int((time.perf_counter() - started) * 1000)
        status = "completed" if not errors else ("failed" if not merged else "completed")
        return RelationExtractionResult(
            document_id=chunks[0].document_id,
            chunk_id=None,
            relations=list(merged.values()),
            model_name=self._result_model_name(),
            latency_ms=latency_ms,
            status=status,
            errors=errors,
        )

    async def extract(self, content: str) -> list[GraphRelation]:
        """Backward-compatible async wrapper."""
        return self.extract_relations(content, [])

    def _extract_llm_relations(
        self,
        text: str,
        entities: list[GraphEntity],
        entity_index: dict[str, GraphEntity],
    ) -> list[GraphRelation]:
        if not self.use_llm:
            return []
        prompt = self._build_llm_prompt(text, entities)
        system_prompt = (
            "Extract relationships between entities. Return JSON ONLY as an array of: "
            "{\"source\":\"...\",\"relation\":\"...\",\"target\":\"...\",\"properties\":{}}. "
            "Allowed relations: USES, DEPENDS_ON, PART_OF, IMPLEMENTS, RELATED_TO, PROVIDES, MENTIONS."
        )
        try:
            payload = self.claude_client.generate_json(prompt=prompt, system_prompt=system_prompt)
        except (ClaudeClientConfigurationError, ClaudeClientAPIError) as exc:
            logger.info("llm_relation_extraction_unavailable", extra={"error": str(exc)})
            return []
        except Exception as exc:
            logger.warning("llm_relation_extraction_failed", extra={"error": str(exc)})
            return []

        if not isinstance(payload, list):
            logger.warning("llm_relation_payload_invalid_type", extra={"type": type(payload).__name__})
            return []

        relations: list[GraphRelation] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            source_name = self._normalize_name(str(item.get("source", "")))
            target_name = self._normalize_name(str(item.get("target", "")))
            relation = str(item.get("relation", "")).strip().upper()
            properties = item.get("properties", {})
            if relation not in ALLOWED_RELATIONS:
                continue
            source_entity = entity_index.get(source_name)
            target_entity = entity_index.get(target_name)
            if source_entity is None or target_entity is None:
                continue
            if source_entity.entity_id == target_entity.entity_id:
                continue
            if not isinstance(properties, dict):
                properties = {}
            relations.append(
                GraphRelation(
                    source_entity_id=source_entity.entity_id,
                    target_entity_id=target_entity.entity_id,
                    relation_type=relation,
                    confidence=0.85,
                    evidence=self._truncate_evidence(properties.get("evidence") or ""),
                    metadata_json={"source": "claude", "properties": properties},
                )
            )
        return relations

    def _extract_regex_relations(
        self,
        text: str,
        entity_index: dict[str, GraphEntity],
    ) -> list[GraphRelation]:
        relations: list[GraphRelation] = []
        for pattern, relation_type in REGEX_RULES:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                source_name_raw = match.group("source")
                target_name_raw = match.group("target")
                source_entity = self._resolve_entity_by_text(source_name_raw, entity_index)
                target_entity = self._resolve_entity_by_text(target_name_raw, entity_index)
                if source_entity is None or target_entity is None:
                    continue
                if source_entity.entity_id == target_entity.entity_id:
                    continue
                relations.append(
                    GraphRelation(
                        source_entity_id=source_entity.entity_id,
                        target_entity_id=target_entity.entity_id,
                        relation_type=relation_type,
                        confidence=0.60,
                        evidence=self._truncate_evidence(match.group(0)),
                        metadata_json={"source": "regex", "pattern": pattern},
                    )
                )
        return relations

    def _build_llm_prompt(self, text: str, entities: list[GraphEntity]) -> str:
        snippet = text[:6000]
        entity_list = [{"name": entity.name, "type": entity.entity_type} for entity in entities[:200]]
        return (
            "Extract relations among these entities from the text.\n"
            f"Entities: {entity_list}\n"
            f"Text:\n{snippet}\n\n"
            "Return JSON only."
        )

    def _build_entity_index(self, entities: list[GraphEntity]) -> dict[str, GraphEntity]:
        index: dict[str, GraphEntity] = {}
        for entity in entities:
            index[self._normalize_name(entity.name)] = entity
            for alias in entity.aliases:
                alias_key = self._normalize_name(alias)
                if alias_key and alias_key not in index:
                    index[alias_key] = entity
        return index

    def _resolve_entity_by_text(self, text: str, entity_index: dict[str, GraphEntity]) -> GraphEntity | None:
        normalized = self._normalize_name(text)
        if not normalized:
            return None
        exact = entity_index.get(normalized)
        if exact is not None:
            return exact
        # fuzzy containment fallback
        for key, entity in entity_index.items():
            if key in normalized or normalized in key:
                return entity
        return None

    def _merge_relations(self, primary: list[GraphRelation], secondary: list[GraphRelation]) -> list[GraphRelation]:
        merged: dict[str, GraphRelation] = {}
        for relation in primary + secondary:
            key = self._relation_key(relation)
            existing = merged.get(key)
            if existing is None or relation.confidence > existing.confidence:
                merged[key] = relation
        return list(merged.values())

    def _relation_key(self, relation: GraphRelation) -> str:
        return f"{relation.source_entity_id}:{relation.relation_type}:{relation.target_entity_id}"

    def _normalize_name(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower())

    def _truncate_evidence(self, value: str) -> str | None:
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned[:2000]

    def _result_model_name(self) -> str:
        if self.use_llm:
            return self.claude_client.model
        return "regex-fallback"
