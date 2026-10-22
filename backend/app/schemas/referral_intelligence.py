from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


ReferralTagColor = Literal["blue", "violet", "cyan", "green", "orange", "pink", "gold", "gray"]
ReferralLifecycleStatus = Literal[
    "created",
    "invite_opened",
    "wallet_connected",
    "qora_activated",
    "first_microtask_completed",
    "first_achievement_unlocked",
]
ReferralChatSenderRole = Literal["referrer", "invitee"]
ReferralChatDeliveryStatus = Literal["sent", "delivered", "read"]
AgentContextSignalSource = Literal["referrer_reported"]
AgentContextSignalConfidence = Literal["low", "medium", "high"]


class ReferralDashboardStatsResponse(BaseModel):
    total_invites: int = Field(ge=0)
    activated_qora: int = Field(ge=0)
    first_microtask: int = Field(ge=0)
    first_achievement: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class ReferralPersonalizationProfile(BaseModel):
    invitee_relationship: str = Field(min_length=1, max_length=120)
    familiarity_level: str = Field(min_length=1, max_length=120)
    invitation_reason: str = Field(min_length=1, max_length=240)
    primary_motivation: str = Field(min_length=1, max_length=240)
    web3_familiarity_level: str = Field(min_length=1, max_length=120)
    previous_web3_tool_experience: str = Field(min_length=1, max_length=240)
    readiness_to_take_action: str = Field(min_length=1, max_length=120)
    concerns_and_frictions: list[str] = Field(default_factory=list)
    previous_negative_experience: str = Field(min_length=1, max_length=120)
    preferred_information_style: str = Field(min_length=1, max_length=120)
    suggested_ecosystem_section: str = Field(min_length=1, max_length=120)
    conversion_likelihood: str = Field(min_length=1, max_length=120)
    additional_note: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReferralDerivedAgentSignal(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: str | list[str]
    source: AgentContextSignalSource = "referrer_reported"
    confidence: AgentContextSignalConfidence = "medium"

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgentMemoryContextInput(BaseModel):
    referral_link_id: UUID
    invite_code: str = Field(min_length=1, max_length=64)
    owner_user_id: UUID
    invitee_user_id: UUID | None = None
    signals: list[ReferralDerivedAgentSignal] = Field(default_factory=list)
    source: Literal["referral_personalization"] = "referral_personalization"
    source_label: AgentContextSignalSource = "referrer_reported"
    created_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReferralLinkSummaryResponse(BaseModel):
    id: UUID
    owner_user_id: UUID
    invite_code: str = Field(min_length=1, max_length=64)
    short_url: str = Field(min_length=1, max_length=2048)
    label: str = Field(min_length=1, max_length=120)
    color: ReferralTagColor
    is_customized: bool
    created_at: datetime
    latest_status: ReferralLifecycleStatus
    unread_message_count: int = Field(ge=0)
    chat_enabled: bool
    progress_percent: int = Field(ge=0, le=100)

    model_config = ConfigDict(extra="forbid")


class ReferralLinksListResponse(BaseModel):
    links: list[ReferralLinkSummaryResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class CreateReferralLinkRequest(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    color: ReferralTagColor = "blue"

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UpdateReferralLinkRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    color: ReferralTagColor | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("label")
    @classmethod
    def _normalize_optional_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized if normalized else None


class CreateCustomizedReferralLinkRequest(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    color: ReferralTagColor = "violet"
    personalization_profile: ReferralPersonalizationProfile

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReferralProgressEventResponse(BaseModel):
    id: UUID
    referral_link_id: UUID
    status: ReferralLifecycleStatus
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    occurred_at: datetime | None = None
    metadata: dict[str, str] | None = None

    model_config = ConfigDict(extra="forbid")


class ReferralProgressEventsResponse(BaseModel):
    events: list[ReferralProgressEventResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ReferralTranslationMetadata(BaseModel):
    source_language: str = Field(min_length=1, max_length=16)
    target_language: str = Field(min_length=1, max_length=16)
    provider: str = Field(min_length=1, max_length=64)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    translated_at: datetime

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReferralChatMessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    referral_link_id: UUID
    sender_role: ReferralChatSenderRole
    body: str = Field(min_length=1, max_length=10_000)
    original_text: str = Field(min_length=1, max_length=10_000)
    original_locale: str = Field(min_length=1, max_length=16)
    source_language: str | None = Field(default=None, max_length=16)
    translated_text: str | None = None
    translated_text_for_viewer: str | None = None
    translation: ReferralTranslationMetadata | None = None
    delivery_status: ReferralChatDeliveryStatus = "sent"
    metadata: dict[str, str] | None = None
    is_read_by_owner: bool
    is_read_by_invitee: bool
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class ReferralChatThreadSummaryResponse(BaseModel):
    id: UUID
    referral_link_id: UUID
    owner_user_id: UUID
    invitee_display_name: str | None = None
    invitee_wallet_address: str | None = None
    latest_message_at: datetime | None = None
    unread_message_count: int = Field(ge=0)
    current_user_role: ReferralChatSenderRole
    messages: list[ReferralChatMessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class SendReferralChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    sender_role: ReferralChatSenderRole | None = None
    source_language: str | None = Field(default=None, max_length=16)
    original_locale: str | None = Field(default=None, max_length=16)
    metadata: dict[str, str] | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TranslateReferralChatMessageRequest(BaseModel):
    message_id: UUID
    target_language: str = Field(min_length=1, max_length=16)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TranslateReferralChatMessageResponse(BaseModel):
    message_id: UUID
    translated_text: str = Field(min_length=1, max_length=10_000)
    translation: ReferralTranslationMetadata

    model_config = ConfigDict(extra="forbid")


class RecordReferralWalletConnectionRequest(BaseModel):
    wallet_address: str = Field(min_length=1, max_length=128)
    invitee_display_name: str | None = Field(default=None, max_length=120)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgentMemoryEnrichmentPayload(BaseModel):
    referral_link_id: UUID
    invite_code: str = Field(min_length=1, max_length=64)
    owner_user_id: UUID
    personalization_profile: ReferralPersonalizationProfile
    latest_status: ReferralLifecycleStatus
    source: Literal["referral_customization"]
    signals: list[ReferralDerivedAgentSignal] = Field(default_factory=list)
    agent_context: AgentMemoryContextInput
    enriched_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class SyncPersonalizationToMemoryRequest(BaseModel):
    referral_link_id: UUID
    metadata: dict[str, str] | None = None

    model_config = ConfigDict(extra="forbid")


class SyncPersonalizationToMemoryResponse(BaseModel):
    synced: bool
    payload: AgentMemoryEnrichmentPayload

    model_config = ConfigDict(extra="forbid")
