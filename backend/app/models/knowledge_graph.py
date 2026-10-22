"""Knowledge graph record ORM model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class KnowledgeGraphRecord(Base):
    """Stores KG extraction/index status per document/chunk."""

    __tablename__ = "knowledge_graph_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    entity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    document: Mapped["Document"] = relationship("Document", back_populates="knowledge_graph_records")
    chunk: Mapped["Chunk | None"] = relationship("Chunk", back_populates="knowledge_graph_records")
