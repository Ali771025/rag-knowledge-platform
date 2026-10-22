"""Internal RAG types and enums.

These types define stable vocabulary used across RAG schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import TypeAlias

TraceId: TypeAlias = str
SourceId: TypeAlias = str
ChunkId: TypeAlias = str
FactId: TypeAlias = str
GraphEvidenceId: TypeAlias = str


class ConfidenceLevel(str, Enum):
    """Normalized confidence labels for grounding and answer quality."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RetrievalSource(str, Enum):
    """Primary retrieval strategy/source labels for traceability."""

    VECTOR = "vector"
    KEYWORD = "keyword"
    GRAPH = "graph"
    HYBRID = "hybrid"
    RULE = "rule"
