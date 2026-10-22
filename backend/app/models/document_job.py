"""Document background processing bookkeeping ORM model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

DocumentJobStatus = Literal["pending", "running", "completed", "failed"]


class DocumentProcessingJob(Base):
    """Tracks asynchronous processing progress for a document."""

    __tablename__ = "document_processing_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    processing_status: Mapped[DocumentJobStatus] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    embedding_status: Mapped[DocumentJobStatus] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    graph_status: Mapped[DocumentJobStatus] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
