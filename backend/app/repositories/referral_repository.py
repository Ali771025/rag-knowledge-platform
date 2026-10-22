from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.invite import Invite
from app.models.referral import (
    ReferralChatMessage,
    ReferralChatMessageTranslation,
    ReferralChatThread,
    ReferralLink,
    ReferralProgressEvent,
)


class ReferralRepository:
    def list_links_by_owner(self, db: Session, owner_user_id: UUID) -> list[ReferralLink]:
        stmt = (
            select(ReferralLink)
            .where(ReferralLink.owner_user_id == owner_user_id)
            .order_by(desc(ReferralLink.created_at))
            .options(
                selectinload(ReferralLink.progress_events),
                selectinload(ReferralLink.chat_thread)
                .selectinload(ReferralChatThread.messages)
                .selectinload(ReferralChatMessage.translations),
            )
        )
        return list(db.scalars(stmt).all())

    def get_link_by_id(self, db: Session, owner_user_id: UUID, referral_link_id: UUID) -> ReferralLink | None:
        stmt = (
            select(ReferralLink)
            .where(and_(ReferralLink.id == referral_link_id, ReferralLink.owner_user_id == owner_user_id))
            .options(
                selectinload(ReferralLink.progress_events),
                selectinload(ReferralLink.chat_thread)
                .selectinload(ReferralChatThread.messages)
                .selectinload(ReferralChatMessage.translations),
            )
        )
        return db.scalar(stmt)

    def get_link_for_participant(self, db: Session, user_id: UUID, referral_link_id: UUID) -> ReferralLink | None:
        stmt = (
            select(ReferralLink)
            .outerjoin(Invite, Invite.code == ReferralLink.invite_code)
            .where(
                and_(
                    ReferralLink.id == referral_link_id,
                    (ReferralLink.owner_user_id == user_id) | (Invite.used_by_user_id == user_id),
                )
            )
            .options(
                selectinload(ReferralLink.progress_events),
                selectinload(ReferralLink.chat_thread)
                .selectinload(ReferralChatThread.messages)
                .selectinload(ReferralChatMessage.translations),
            )
        )
        return db.scalar(stmt)

    def get_link_by_invite_code(self, db: Session, invite_code: str) -> ReferralLink | None:
        stmt = (
            select(ReferralLink)
            .where(ReferralLink.invite_code == invite_code)
            .options(
                selectinload(ReferralLink.progress_events),
                selectinload(ReferralLink.chat_thread)
                .selectinload(ReferralChatThread.messages)
                .selectinload(ReferralChatMessage.translations),
            )
        )
        return db.scalar(stmt)

    def get_referral_invite(self, db: Session, invite_code: str) -> Invite | None:
        return db.scalar(select(Invite).where(Invite.code == invite_code))

    def create_link(
        self,
        db: Session,
        *,
        owner_user_id: UUID,
        invite_code: str,
        short_url: str,
        label: str,
        color: str,
        is_customized: bool,
        personalization_profile: dict[str, object] | None,
    ) -> ReferralLink:
        link = ReferralLink(
            owner_user_id=owner_user_id,
            invite_code=invite_code,
            short_url=short_url,
            label=label,
            color=color,
            is_customized=is_customized,
            personalization_profile=personalization_profile,
            latest_status="created",
            progress_percent=0,
            chat_enabled=False,
        )
        db.add(link)
        db.add(
            Invite(
                code=invite_code,
                is_used=False,
                expires_at=None,
                email=None,
                is_active=True,
            )
        )
        db.commit()
        db.refresh(link)
        return link

    def update_link(
        self,
        db: Session,
        *,
        link: ReferralLink,
        label: str | None = None,
        color: str | None = None,
    ) -> ReferralLink:
        if label is not None:
            link.label = label
        if color is not None:
            link.color = color
        link.updated_at = datetime.now(timezone.utc)
        db.add(link)
        db.commit()
        db.refresh(link)
        return link

    def add_progress_event(
        self,
        db: Session,
        *,
        referral_link_id: UUID,
        status: str,
        title: str,
        description: str | None = None,
        occurred_at: datetime | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ReferralProgressEvent:
        event = ReferralProgressEvent(
            referral_link_id=referral_link_id,
            status=status,
            title=title,
            description=description,
            occurred_at=occurred_at,
            metadata_json=metadata or {},
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def list_progress_events(
        self,
        db: Session,
        *,
        referral_link_id: UUID,
    ) -> list[ReferralProgressEvent]:
        stmt = (
            select(ReferralProgressEvent)
            .where(ReferralProgressEvent.referral_link_id == referral_link_id)
            .order_by(ReferralProgressEvent.created_at.asc())
        )
        return list(db.scalars(stmt).all())

    def get_or_create_chat_thread(
        self,
        db: Session,
        *,
        referral_link_id: UUID,
        owner_user_id: UUID,
    ) -> ReferralChatThread:
        stmt = (
            select(ReferralChatThread)
            .where(ReferralChatThread.referral_link_id == referral_link_id)
            .options(selectinload(ReferralChatThread.messages).selectinload(ReferralChatMessage.translations))
        )
        existing = db.scalar(stmt)
        if existing is not None:
            return existing

        thread = ReferralChatThread(
            referral_link_id=referral_link_id,
            owner_user_id=owner_user_id,
            latest_message_at=None,
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)
        return thread

    def list_chat_messages(self, db: Session, *, thread_id: UUID) -> list[ReferralChatMessage]:
        stmt = (
            select(ReferralChatMessage)
            .where(ReferralChatMessage.thread_id == thread_id)
            .order_by(ReferralChatMessage.created_at.asc())
            .options(selectinload(ReferralChatMessage.translations))
        )
        return list(db.scalars(stmt).all())

    def add_chat_message(
        self,
        db: Session,
        *,
        thread_id: UUID,
        referral_link_id: UUID,
        sender_role: str,
        body: str,
        source_language: str | None,
        metadata: dict[str, str] | None = None,
    ) -> ReferralChatMessage:
        message = ReferralChatMessage(
            thread_id=thread_id,
            referral_link_id=referral_link_id,
            sender_role=sender_role,
            body=body,
            source_language=source_language,
            metadata_json=metadata or {},
            is_read_by_owner=sender_role == "referrer",
            is_read_by_invitee=sender_role == "invitee",
        )
        db.add(message)

        thread = db.get(ReferralChatThread, thread_id)
        if thread is not None:
            now = datetime.now(timezone.utc)
            thread.latest_message_at = now
            thread.updated_at = now
            db.add(thread)

        db.commit()
        db.refresh(message)
        return message

    def get_message_translation(
        self,
        db: Session,
        *,
        message_id: UUID,
        target_locale: str,
    ) -> ReferralChatMessageTranslation | None:
        stmt = select(ReferralChatMessageTranslation).where(
            and_(
                ReferralChatMessageTranslation.message_id == message_id,
                ReferralChatMessageTranslation.target_locale == target_locale,
            )
        )
        return db.scalar(stmt)

    def upsert_message_translation(
        self,
        db: Session,
        *,
        message: ReferralChatMessage,
        source_locale: str,
        target_locale: str,
        translated_text: str,
        provider: str,
        confidence: float | None,
    ) -> ReferralChatMessageTranslation:
        translation = self.get_message_translation(db, message_id=message.id, target_locale=target_locale)
        if translation is None:
            translation = ReferralChatMessageTranslation(
                message_id=message.id,
                referral_link_id=message.referral_link_id,
                source_locale=source_locale,
                target_locale=target_locale,
                translated_text=translated_text,
                provider=provider,
                confidence=confidence,
            )
        else:
            translation.source_locale = source_locale
            translation.translated_text = translated_text
            translation.provider = provider
            translation.confidence = confidence

        db.add(translation)
        db.commit()
        db.refresh(translation)
        return translation

    def mark_chat_messages_read(
        self,
        db: Session,
        *,
        thread_id: UUID,
        reader_role: str,
    ) -> ReferralChatThread | None:
        thread = db.get(ReferralChatThread, thread_id)
        if thread is None:
            return None

        messages = self.list_chat_messages(db, thread_id=thread_id)
        for message in messages:
            if reader_role == "referrer" and message.sender_role != "referrer":
                message.is_read_by_owner = True
                db.add(message)
            if reader_role == "invitee" and message.sender_role != "invitee":
                message.is_read_by_invitee = True
                db.add(message)

        thread.updated_at = datetime.now(timezone.utc)
        db.add(thread)
        db.commit()
        db.refresh(thread)
        thread.messages = messages
        return thread

    def update_chat_thread_invitee(
        self,
        db: Session,
        *,
        thread: ReferralChatThread,
        invitee_display_name: str | None,
        invitee_wallet_address: str | None,
    ) -> ReferralChatThread:
        thread.invitee_display_name = invitee_display_name
        thread.invitee_wallet_address = invitee_wallet_address
        thread.updated_at = datetime.now(timezone.utc)
        db.add(thread)
        db.commit()
        db.refresh(thread)
        return thread

    def update_chat_message_translation(
        self,
        db: Session,
        *,
        message: ReferralChatMessage,
        target_language: str,
        translated_text: str,
        translation_provider: str,
        translation_confidence: float | None,
    ) -> ReferralChatMessage:
        message.target_language = target_language
        message.translated_text = translated_text
        message.translation_provider = translation_provider
        message.translation_confidence = translation_confidence
        message.translation_created_at = datetime.now(timezone.utc)
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    def get_chat_message_by_id(
        self,
        db: Session,
        *,
        thread_id: UUID,
        message_id: UUID,
    ) -> ReferralChatMessage | None:
        stmt = select(ReferralChatMessage).where(
            and_(
                ReferralChatMessage.thread_id == thread_id,
                ReferralChatMessage.id == message_id,
            )
        ).options(selectinload(ReferralChatMessage.translations))
        return db.scalar(stmt)

    def compute_dashboard_stats(self, db: Session, *, owner_user_id: UUID) -> dict[str, int]:
        total_links_stmt = select(func.count(ReferralLink.id)).where(ReferralLink.owner_user_id == owner_user_id)
        activated_stmt = select(func.count(ReferralLink.id)).where(
            and_(
                ReferralLink.owner_user_id == owner_user_id,
                ReferralLink.latest_status.in_(
                    [
                        "qora_activated",
                        "first_microtask_completed",
                        "first_achievement_unlocked",
                    ]
                ),
            )
        )
        first_microtask_stmt = select(func.count(ReferralLink.id)).where(
            and_(
                ReferralLink.owner_user_id == owner_user_id,
                ReferralLink.latest_status.in_(
                    [
                        "first_microtask_completed",
                        "first_achievement_unlocked",
                    ]
                ),
            )
        )
        first_achievement_stmt = select(func.count(ReferralLink.id)).where(
            and_(
                ReferralLink.owner_user_id == owner_user_id,
                ReferralLink.latest_status == "first_achievement_unlocked",
            )
        )
        return {
            "total_invites": int(db.scalar(total_links_stmt) or 0),
            "activated_qora": int(db.scalar(activated_stmt) or 0),
            "first_microtask": int(db.scalar(first_microtask_stmt) or 0),
            "first_achievement": int(db.scalar(first_achievement_stmt) or 0),
        }
