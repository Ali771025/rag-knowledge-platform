"""RAG configuration persistence model for admin controls."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


class RAGConfiguration(Base):
    """Stores mutable admin-level RAG configuration."""

    __tablename__ = "rag_configurations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False, default=900)
    chunk_overlap: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    similarity_threshold: Mapped[float] = mapped_column(nullable=False, default=0.35)
    reranker_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hybrid_search_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    graph_enhanced_retrieval_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False, default="text-embedding-3-large")
    reranker_model: Mapped[str] = mapped_column(String(255), nullable=False, default="heuristic-v1")
    vector_collection_name: Mapped[str] = mapped_column(String(255), nullable=False, default="knowledge_base")
    default_labels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
