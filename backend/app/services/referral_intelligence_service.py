from __future__ import annotations

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy.orm import Session

from app.models.referral import (
    ReferralChatMessage,
    ReferralChatMessageTranslation,
    ReferralChatThread,
    ReferralLink,
    ReferralProgressEvent,
)
from app.repositories.referral_repository import ReferralRepository
from app.schemas.referral_intelligence import (
    AgentMemoryContextInput,
    AgentMemoryEnrichmentPayload,
    ReferralDerivedAgentSignal,
    ReferralPersonalizationProfile,
)


class ReferralIntelligenceDomainError(ValueError):
    pass


class ReferralLinkNotFoundError(ReferralIntelligenceDomainError):
    pass


class ReferralChatUnavailableError(ReferralIntelligenceDomainError):
    pass


class ReferralChatParticipantMismatchError(ReferralIntelligenceDomainError):
    pass


ReferralChatParticipantRole = str


class ReferralIntelligenceService:
    _STATUS_PROGRESS_MAP: dict[str, int] = {
        "created": 0,
        "invite_opened": 20,
        "wallet_connected": 40,
        "qora_activated": 60,
        "first_microtask_completed": 80,
        "first_achievement_unlocked": 100,
    }

    _STATUS_TITLE_MAP: dict[str, str] = {
        "created": "Link created",
        "invite_opened": "Invited",
        "wallet_connected": "Connected Wallet",
        "qora_activated": "Activated QORA",
        "first_microtask_completed": "First Micro-task",
        "first_achievement_unlocked": "First Achievement",
    }
    _MILESTONE_STATUSES: tuple[str, ...] = (
        "invite_opened",
        "wallet_connected",
        "qora_activated",
        "first_microtask_completed",
        "first_achievement_unlocked",
    )
    _CURRENT_MILESTONE_INDEX_BY_STATUS: dict[str, int] = {
        "created": 0,
        "invite_opened": 1,
        "wallet_connected": 2,
        "qora_activated": 3,
        "first_microtask_completed": 4,
        "first_achievement_unlocked": 5,
    }
    _CHAT_ENABLED_STATUSES: set[str] = {
        "wallet_connected",
        "qora_activated",
        "first_microtask_completed",
        "first_achievement_unlocked",
    }
    _SUPPORTED_TRANSLATION_LOCALES: set[str] = {"en", "fa", "ar"}
    _TRANSLATION_PROVIDER = "internal_referral_dictionary_v1"
    _TRANSLATION_PHRASES: dict[tuple[str, str, str], str] = {
        ("en", "fa", "hello"): "سلام",
        ("en", "fa", "hi"): "سلام",
        ("en", "fa", "thanks"): "ممنون",
        ("en", "fa", "thank you"): "ممنون",
        ("en", "fa", "hello invitee"): "سلام دعوت‌شونده",
        ("fa", "en", "سلام"): "Hello",
        ("fa", "en", "ممنون"): "Thanks",
        ("fa", "en", "متشکرم"): "Thank you",
        ("en", "ar", "hello"): "مرحبًا",
        ("en", "ar", "hi"): "مرحبًا",
        ("en", "ar", "thanks"): "شكرًا",
        ("ar", "en", "مرحبا"): "Hello",
        ("ar", "en", "مرحبًا"): "Hello",
        ("ar", "en", "شكرا"): "Thanks",
        ("ar", "en", "شكرًا"): "Thanks",
    }
    _AGENT_SIGNAL_FIELD_MAP: tuple[tuple[str, str, str], ...] = (
        ("relationship_context", "invitee_relationship", "medium"),
        ("familiarity_confidence", "familiarity_level", "medium"),
        ("reason_for_invitation", "invitation_reason", "medium"),
        ("motivation", "primary_motivation", "medium"),
        ("web3_familiarity", "web3_familiarity_level", "medium"),
        ("previous_experience", "previous_web3_tool_experience", "low"),
        ("readiness", "readiness_to_take_action", "medium"),
        ("concerns", "concerns_and_frictions", "low"),
        ("negative_history", "previous_negative_experience", "low"),
        ("preferred_information_style", "preferred_information_style", "medium"),
        ("suggested_ecosystem_section", "suggested_ecosystem_section", "medium"),
        ("estimated_conversion_likelihood", "conversion_likelihood", "medium"),
        ("additional_note", "additional_note", "low"),
    )

    def __init__(self, repository: ReferralRepository | None = None) -> None:
        self.repository = repository or ReferralRepository()

    def get_dashboard_stats(self, db: Session, owner_user_id: UUID) -> dict[str, int]:
        return self.repository.compute_dashboard_stats(db, owner_user_id=owner_user_id)

    def list_links(self, db: Session, owner_user_id: UUID) -> list[ReferralLink]:
        return self.repository.list_links_by_owner(db, owner_user_id)

    def create_regular_link(
        self,
        db: Session,
        *,
        owner_user_id: UUID,
        label: str,
        color: str,
    ) -> ReferralLink:
        invite_code = self._generate_invite_code()
        short_url = self._build_short_url(invite_code)
        link = self.repository.create_link(
            db,
            owner_user_id=owner_user_id,
            invite_code=invite_code,
            short_url=short_url,
            label=label,
            color=color,
            is_customized=False,
            personalization_profile=None,
        )
        self.repository.add_progress_event(
            db,
            referral_link_id=link.id,
            status="created",
            title=self._STATUS_TITLE_MAP["created"],
            occurred_at=datetime.now(timezone.utc),
            metadata={"source": "regular_link_creation"},
        )
        return self.repository.get_link_by_id(db, owner_user_id, link.id) or link

    def create_customized_link(
        self,
        db: Session,
        *,
        owner_user_id: UUID,
        label: str,
        color: str,
        personalization_profile: ReferralPersonalizationProfile,
    ) -> ReferralLink:
        invite_code = self._generate_invite_code()
        short_url = self._build_short_url(invite_code)
        link = self.repository.create_link(
            db,
            owner_user_id=owner_user_id,
            invite_code=invite_code,
            short_url=short_url,
            label=label,
            color=color,
            is_customized=True,
            personalization_profile=personalization_profile.model_dump(mode="python"),
        )
        self.repository.add_progress_event(
            db,
            referral_link_id=link.id,
            status="created",
            title=self._STATUS_TITLE_MAP["created"],
            occurred_at=datetime.now(timezone.utc),
            metadata={"source": "customized_link_creation"},
        )
        return self.repository.get_link_by_id(db, owner_user_id, link.id) or link

    def update_link(
        self,
        db: Session,
        *,
        owner_user_id: UUID,
        referral_link_id: UUID,
        label: str | None,
        color: str | None,
    ) -> ReferralLink:
        link = self.repository.get_link_by_id(db, owner_user_id, referral_link_id)
        if link is None:
            raise ReferralLinkNotFoundError("Referral link not found")

        if label is None and color is None:
            return link

        updated = self.repository.update_link(db, link=link, label=label, color=color)
        return self.repository.get_link_by_id(db, owner_user_id, updated.id) or updated

    def list_progress_events(
        self,
        db: Session,
        *,
        owner_user_id: UUID,
        referral_link_id: UUID,
    ) -> list[ReferralProgressEvent]:
        link = self.repository.get_link_by_id(db, owner_user_id, referral_link_id)
        if link is None:
            raise ReferralLinkNotFoundError("Referral link not found")
        raw_events = self.repository.list_progress_events(db, referral_link_id=referral_link_id)
        events_by_status: dict[str, ReferralProgressEvent] = {}
        for event in raw_events:
            if event.status not in self._MILESTONE_STATUSES:
                continue
            existing = events_by_status.get(event.status)
            if existing is None:
                events_by_status[event.status] = event
                continue
            existing_occurred = existing.occurred_at or existing.created_at
            candidate_occurred = event.occurred_at or event.created_at
            if candidate_occurred < existing_occurred:
                events_by_status[event.status] = event

        current_milestone_index = self._CURRENT_MILESTONE_INDEX_BY_STATUS.get(link.latest_status, 0)
        now = datetime.now(timezone.utc)
        timeline: list[ReferralProgressEvent] = []

        for milestone_index, status in enumerate(self._MILESTONE_STATUSES):
            source_event = events_by_status.get(status)
            if milestone_index < current_milestone_index:
                milestone_state = "completed"
            elif milestone_index == current_milestone_index:
                milestone_state = "current"
            else:
                milestone_state = "upcoming"

            metadata: dict[str, str] = {"milestone_state": milestone_state}
            if source_event is not None and source_event.metadata_json:
                metadata.update(source_event.metadata_json)

            timeline.append(
                ReferralProgressEvent(
                    id=source_event.id if source_event is not None else uuid5(NAMESPACE_URL, f"{referral_link_id}:{status}"),
                    referral_link_id=referral_link_id,
                    status=status,
                    title=self._STATUS_TITLE_MAP[status],
                    description=source_event.description if source_event is not None else None,
                    occurred_at=source_event.occurred_at if source_event is not None else None,
                    metadata_json=metadata,
                    created_at=source_event.created_at if source_event is not None else now,
                )
            )

        return timeline

    def get_chat_thread(
        self,
        db: Session,
        *,
        participant_user_id: UUID,
        referral_link_id: UUID,
        viewer_locale: str | None = None,
    ) -> tuple[ReferralChatThread, ReferralChatParticipantRole]:
        link, participant_role = self._get_chat_link_for_participant(
            db,
            participant_user_id=participant_user_id,
            referral_link_id=referral_link_id,
            require_chat_enabled=True,
        )
        thread = self.repository.get_or_create_chat_thread(
            db,
            referral_link_id=referral_link_id,
            owner_user_id=link.owner_user_id,
        )
        if viewer_locale is not None:
            self.ensure_thread_translations(db, thread=thread, viewer_locale=viewer_locale)
            thread.messages = self.repository.list_chat_messages(db, thread_id=thread.id)
        return thread, participant_role

    def send_chat_message(
        self,
        db: Session,
        *,
        participant_user_id: UUID,
        referral_link_id: UUID,
        requested_sender_role: str | None,
        body: str,
        source_language: str | None,
        metadata: dict[str, str] | None,
    ) -> ReferralChatMessage:
        link, participant_role = self._get_chat_link_for_participant(
            db,
            participant_user_id=participant_user_id,
            referral_link_id=referral_link_id,
            require_chat_enabled=True,
        )
        if requested_sender_role is not None and requested_sender_role != participant_role:
            raise ReferralChatParticipantMismatchError("Sender role does not match the authenticated referral participant")

        normalized_body = body.strip()
        if not normalized_body:
            raise ReferralIntelligenceDomainError("Referral chat message cannot be empty")

        original_locale = self._normalize_locale(source_language or self._detect_locale(normalized_body))
        thread = self.repository.get_or_create_chat_thread(
            db,
            referral_link_id=referral_link_id,
            owner_user_id=link.owner_user_id,
        )
        message = self.repository.add_chat_message(
            db,
            thread_id=thread.id,
            referral_link_id=referral_link_id,
            sender_role=participant_role,
            body=normalized_body,
            source_language=original_locale,
            metadata=metadata,
        )
        return message

    def mark_chat_thread_read(
        self,
        db: Session,
        *,
        participant_user_id: UUID,
        referral_link_id: UUID,
        viewer_locale: str | None = None,
    ) -> tuple[ReferralChatThread, ReferralChatParticipantRole]:
        thread, participant_role = self.get_chat_thread(
            db,
            participant_user_id=participant_user_id,
            referral_link_id=referral_link_id,
            viewer_locale=viewer_locale,
        )
        updated = self.repository.mark_chat_messages_read(db, thread_id=thread.id, reader_role=participant_role)
        return updated or thread, participant_role

    def record_wallet_connection(
        self,
        db: Session,
        *,
        participant_user_id: UUID,
        referral_link_id: UUID,
        wallet_address: str,
        invitee_display_name: str | None,
    ) -> ReferralLink:
        link, participant_role = self._get_chat_link_for_participant(
            db,
            participant_user_id=participant_user_id,
            referral_link_id=referral_link_id,
            require_chat_enabled=False,
        )
        if participant_role != "invitee":
            raise ReferralChatParticipantMismatchError("Only the invitee can connect a wallet for this referral")

        normalized_wallet = wallet_address.strip()
        if not normalized_wallet:
            raise ReferralIntelligenceDomainError("Wallet address is required")

        if link.latest_status not in self._CHAT_ENABLED_STATUSES:
            self._set_link_status(db, link=link, status="wallet_connected")
        else:
            link.chat_enabled = True
            self.repository.update_link(db, link=link)

        if link.chat_thread is not None:
            self.repository.update_chat_thread_invitee(
                db,
                thread=link.chat_thread,
                invitee_display_name=invitee_display_name,
                invitee_wallet_address=normalized_wallet,
            )
        return self.repository.get_link_by_id(db, link.owner_user_id, link.id) or link

    def translate_message(
        self,
        db: Session,
        *,
        participant_user_id: UUID,
        referral_link_id: UUID,
        message_id: UUID,
        target_language: str,
    ) -> ReferralChatMessage:
        thread, _ = self.get_chat_thread(
            db,
            participant_user_id=participant_user_id,
            referral_link_id=referral_link_id,
        )
        message = self.repository.get_chat_message_by_id(db, thread_id=thread.id, message_id=message_id)
        if message is None:
            raise ReferralIntelligenceDomainError("Referral chat message not found")

        translation = self.ensure_message_translation(db, message=message, viewer_locale=target_language)
        if translation is None:
            return message

        updated = self.repository.update_chat_message_translation(
            db,
            message=message,
            target_language=translation.target_locale,
            translated_text=translation.translated_text,
            translation_provider=translation.provider,
            translation_confidence=translation.confidence,
        )
        return updated

    def ensure_thread_translations(self, db: Session, *, thread: ReferralChatThread, viewer_locale: str) -> None:
        target_locale = self._normalize_locale(viewer_locale)
        for message in list(thread.messages or []):
            self.ensure_message_translation(db, message=message, viewer_locale=target_locale)

    def ensure_message_translation(
        self,
        db: Session,
        *,
        message: ReferralChatMessage,
        viewer_locale: str,
    ) -> ReferralChatMessageTranslation | None:
        target_locale = self._normalize_locale(viewer_locale)
        source_locale = self._normalize_locale(message.source_language or self._detect_locale(message.body))
        if source_locale == target_locale:
            return None

        cached = self.repository.get_message_translation(db, message_id=message.id, target_locale=target_locale)
        if cached is not None:
            return cached

        translated_text = self._translate_text(text=message.body, source_locale=source_locale, target_locale=target_locale)
        return self.repository.upsert_message_translation(
            db,
            message=message,
            source_locale=source_locale,
            target_locale=target_locale,
            translated_text=translated_text,
            provider=self._TRANSLATION_PROVIDER,
            confidence=0.72,
        )

    def sync_personalization_to_memory(
        self,
        db: Session,
        *,
        owner_user_id: UUID,
        referral_link_id: UUID,
        metadata: dict[str, str] | None,
    ) -> AgentMemoryEnrichmentPayload:
        link = self.repository.get_link_by_id(db, owner_user_id, referral_link_id)
        if link is None:
            raise ReferralLinkNotFoundError("Referral link not found")
        if not link.personalization_profile:
            raise ReferralIntelligenceDomainError("Personalization profile is not available for this referral link")

        profile = ReferralPersonalizationProfile.model_validate(link.personalization_profile)
        agent_context = self.build_agent_memory_context(
            link=link,
            personalization_profile=profile,
            invitee_user_id=None,
            metadata=metadata,
        )
        payload = AgentMemoryEnrichmentPayload(
            referral_link_id=link.id,
            invite_code=link.invite_code,
            owner_user_id=link.owner_user_id,
            personalization_profile=profile,
            latest_status=link.latest_status,
            source="referral_customization",
            signals=agent_context.signals,
            agent_context=agent_context,
            enriched_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        return payload

    def get_agent_context_by_invite_code(
        self,
        db: Session,
        *,
        invite_code: str,
        current_user_id: UUID | None = None,
        metadata: dict[str, str] | None = None,
    ) -> AgentMemoryContextInput:
        normalized_invite_code = invite_code.strip()
        if not normalized_invite_code:
            raise ReferralLinkNotFoundError("Referral link not found")

        link = self.repository.get_link_by_invite_code(db, normalized_invite_code)
        if link is None:
            raise ReferralLinkNotFoundError("Referral link not found")
        if not link.personalization_profile:
            raise ReferralIntelligenceDomainError("Personalization profile is not available for this referral link")

        invite = self.repository.get_referral_invite(db, link.invite_code)
        invitee_user_id = invite.used_by_user_id if invite is not None else None
        if current_user_id is not None and current_user_id != link.owner_user_id and current_user_id != invitee_user_id:
            raise ReferralLinkNotFoundError("Referral link not found")

        profile = ReferralPersonalizationProfile.model_validate(link.personalization_profile)
        return self.build_agent_memory_context(
            link=link,
            personalization_profile=profile,
            invitee_user_id=invitee_user_id,
            metadata=metadata,
        )

    def build_agent_memory_context(
        self,
        *,
        link: ReferralLink,
        personalization_profile: ReferralPersonalizationProfile,
        invitee_user_id: UUID | None,
        metadata: dict[str, str] | None,
    ) -> AgentMemoryContextInput:
        signals: list[ReferralDerivedAgentSignal] = []
        raw_profile = personalization_profile.model_dump(mode="python")
        for key, field_name, confidence in self._AGENT_SIGNAL_FIELD_MAP:
            value = raw_profile.get(field_name)
            if value is None:
                continue
            if isinstance(value, str):
                normalized_value = value.strip()
                if not normalized_value:
                    continue
                signals.append(
                    ReferralDerivedAgentSignal(
                        key=key,
                        value=normalized_value,
                        source="referrer_reported",
                        confidence=confidence,
                    )
                )
                continue
            if isinstance(value, list):
                normalized_list = [str(item).strip() for item in value if str(item).strip()]
                if normalized_list:
                    signals.append(
                        ReferralDerivedAgentSignal(
                            key=key,
                            value=normalized_list,
                            source="referrer_reported",
                            confidence=confidence,
                        )
                    )

        return AgentMemoryContextInput(
            referral_link_id=link.id,
            invite_code=link.invite_code,
            owner_user_id=link.owner_user_id,
            invitee_user_id=invitee_user_id,
            signals=signals,
            source="referral_personalization",
            source_label="referrer_reported",
            created_at=datetime.now(timezone.utc),
            metadata={
                "source_attribution": "referrer_reported",
                "truth_status": "unverified_referrer_signal",
                **(metadata or {}),
            },
        )

    def _set_link_status(self, db: Session, *, link: ReferralLink, status: str) -> None:
        progress = self._STATUS_PROGRESS_MAP.get(status, link.progress_percent)
        existing_status = link.latest_status
        link.latest_status = status
        link.progress_percent = progress
        link.chat_enabled = progress >= self._STATUS_PROGRESS_MAP.get("wallet_connected", 40)
        self.repository.update_link(db, link=link)
        if existing_status == status:
            return
        self.repository.add_progress_event(
            db,
            referral_link_id=link.id,
            status=status,
            title=self._STATUS_TITLE_MAP.get(status, "Status updated"),
            occurred_at=datetime.now(timezone.utc),
            metadata={"source": "lifecycle_auto_update"},
        )

    def _generate_invite_code(self) -> str:
        raw = uuid4().hex[:10].upper()
        return f"REF-{raw}"

    def _build_short_url(self, invite_code: str) -> str:
        return f"https://example.invalid/register?invite={invite_code}"

    def _normalize_locale(self, locale: str | None) -> str:
        normalized = (locale or "en").strip().lower().replace("_", "-")
        language = normalized.split("-", 1)[0]
        if language in self._SUPPORTED_TRANSLATION_LOCALES:
            return language
        return "en"

    def _detect_locale(self, text: str) -> str:
        if any("\u0600" <= character <= "\u06ff" for character in text):
            return "fa"
        return "en"

    def _translate_text(self, *, text: str, source_locale: str, target_locale: str) -> str:
        normalized_text = " ".join(text.strip().split())
        phrase = self._TRANSLATION_PHRASES.get((source_locale, target_locale, normalized_text.casefold()))
        if phrase is not None:
            return phrase

        if target_locale == "fa":
            return f"ترجمه: {text}"
        if target_locale == "ar":
            return f"ترجمة: {text}"
        return f"Translation: {text}"

    def _get_chat_link_for_participant(
        self,
        db: Session,
        *,
        participant_user_id: UUID,
        referral_link_id: UUID,
        require_chat_enabled: bool,
    ) -> tuple[ReferralLink, ReferralChatParticipantRole]:
        link = self.repository.get_link_for_participant(db, participant_user_id, referral_link_id)
        if link is None:
            raise ReferralLinkNotFoundError("Referral link not found")

        participant_role = self._resolve_participant_role(
            db,
            link=link,
            participant_user_id=participant_user_id,
        )
        if require_chat_enabled and not self._is_chat_enabled(link):
            raise ReferralChatUnavailableError("Referral chat becomes available after wallet connection")
        return link, participant_role

    def _resolve_participant_role(
        self,
        db: Session,
        *,
        link: ReferralLink,
        participant_user_id: UUID,
    ) -> ReferralChatParticipantRole:
        if link.owner_user_id == participant_user_id:
            return "referrer"

        invite = self.repository.get_referral_invite(db, link.invite_code)
        if invite is not None and invite.used_by_user_id == participant_user_id:
            return "invitee"

        raise ReferralLinkNotFoundError("Referral link not found")

    def _is_chat_enabled(self, link: ReferralLink) -> bool:
        return link.chat_enabled or link.latest_status in self._CHAT_ENABLED_STATUSES
