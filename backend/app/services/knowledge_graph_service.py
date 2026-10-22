"""Knowledge graph service orchestration."""

from __future__ import annotations

import logging

from app.ingestion.exceptions import IngestionValidationError
from app.knowledge_graph.graph_retriever import GraphRetriever
from app.knowledge_graph.query_expander import QueryExpander
from app.knowledge_graph.schemas import GraphBuildRequest, GraphBuildResult
from app.schemas.knowledge_graph import (
    GraphContextRequest,
    GraphContextResponse,
    QueryExpansionRequest,
    QueryExpansionResponse,
)

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """Thin service layer for knowledge graph retrieval and query expansion."""

    def __init__(
        self,
        query_expander: QueryExpander | None = None,
        graph_retriever: GraphRetriever | None = None,
    ) -> None:
        self.query_expander = query_expander or QueryExpander()
        self.graph_retriever = graph_retriever or GraphRetriever()

    def expand_query(self, request: QueryExpansionRequest) -> QueryExpansionResponse:
        """Expand a user query using graph-aware related terms."""
        try:
            payload = self.query_expander.expand_query(query=request.query, max_expansions=request.max_expansions)
            expansions = payload.get("expanded_queries") or payload.get("expansions") or []
            metadata_json = {
                "related_entities": payload.get("related_entities", []),
                "graph_hints": payload.get("graph_hints", {}),
                "include_synonyms": request.include_synonyms,
            }
            logger.info(
                "knowledge_graph_query_expanded",
                extra={"query": request.query, "expansion_count": len(expansions)},
            )
            return QueryExpansionResponse(query=request.query, expansions=list(expansions), metadata_json=metadata_json)
        except Exception as exc:
            logger.exception("knowledge_graph_expand_query_failed", exc_info=exc)
            raise IngestionValidationError("failed to expand query") from exc

    def get_graph_context(self, request: GraphContextRequest) -> GraphContextResponse:
        """Retrieve structured graph context for a query."""
        try:
            context = self.graph_retriever.get_context_for_query(request.query, depth=2)
            entities = [entity.model_dump(mode="json") for entity in context.entities][: request.top_k_entities]
            relations = [relation.model_dump(mode="json") for relation in context.relations][: request.top_k_relations]
            paths = [path.model_dump(mode="json") for path in context.paths] if request.include_paths else []

            metadata_json = dict(context.metadata_json or {})
            metadata_json["top_k_entities"] = request.top_k_entities
            metadata_json["top_k_relations"] = request.top_k_relations
            metadata_json["include_paths"] = request.include_paths

            logger.info(
                "knowledge_graph_context_retrieved",
                extra={
                    "query": request.query,
                    "entities": len(entities),
                    "relations": len(relations),
                    "paths": len(paths),
                },
            )
            return GraphContextResponse(
                query=request.query,
                entities=entities,
                relations=relations,
                paths=paths,
                metadata_json=metadata_json,
            )
        except Exception as exc:
            logger.exception("knowledge_graph_get_context_failed", exc_info=exc)
            raise IngestionValidationError("failed to retrieve graph context") from exc

    async def build(self, request: GraphBuildRequest) -> GraphBuildResult:
        """Backward-compatible placeholder for older graph build flow."""
        logger.info("knowledge_graph_build_requested", extra={"document_id": str(request.document_id)})
        return GraphBuildResult(document_id=request.document_id, entities=0, relations=0, status="pending")
