from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReferralLink(Base):
    __tablename__ = "referral_links"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    invite_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    short_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="blue")
    is_customized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latest_status: Mapped[str] = mapped_column(String(64), nullable=False, default="created")
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chat_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    personalization_profile: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
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

    progress_events: Mapped[list["ReferralProgressEvent"]] = relationship(
        "ReferralProgressEvent",
        back_populates="referral_link",
        cascade="all, delete-orphan",
    )
    chat_thread: Mapped["ReferralChatThread | None"] = relationship(
        "ReferralChatThread",
        back_populates="referral_link",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ReferralProgressEvent(Base):
    __tablename__ = "referral_progress_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    referral_link_id: Mapped[UUID] = mapped_column(ForeignKey("referral_links.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, str]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    referral_link: Mapped[ReferralLink] = relationship("ReferralLink", back_populates="progress_events")


class ReferralChatThread(Base):
    __tablename__ = "referral_chat_threads"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    referral_link_id: Mapped[UUID] = mapped_column(
        ForeignKey("referral_links.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    invitee_display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    invitee_wallet_address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latest_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    referral_link: Mapped[ReferralLink] = relationship("ReferralLink", back_populates="chat_thread")
    messages: Mapped[list["ReferralChatMessage"]] = relationship(
        "ReferralChatMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ReferralChatMessage.created_at",
    )


class ReferralChatMessage(Base):
    __tablename__ = "referral_chat_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("referral_chat_threads.id"), nullable=False, index=True)
    referral_link_id: Mapped[UUID] = mapped_column(ForeignKey("referral_links.id"), nullable=False, index=True)
    sender_role: Mapped[str] = mapped_column(String(32), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    translated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    translation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    translation_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, str]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    is_read_by_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_read_by_invitee: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    thread: Mapped[ReferralChatThread] = relationship("ReferralChatThread", back_populates="messages")
    translations: Mapped[list["ReferralChatMessageTranslation"]] = relationship(
        "ReferralChatMessageTranslation",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class ReferralChatMessageTranslation(Base):
    __tablename__ = "referral_chat_message_translations"
    __table_args__ = (UniqueConstraint("message_id", "target_locale", name="uq_referral_chat_message_translation_locale"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(ForeignKey("referral_chat_messages.id"), nullable=False, index=True)
    referral_link_id: Mapped[UUID] = mapped_column(ForeignKey("referral_links.id"), nullable=False, index=True)
    source_locale: Mapped[str] = mapped_column(String(16), nullable=False)
    target_locale: Mapped[str] = mapped_column(String(16), nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    message: Mapped[ReferralChatMessage] = relationship("ReferralChatMessage", back_populates="translations")
