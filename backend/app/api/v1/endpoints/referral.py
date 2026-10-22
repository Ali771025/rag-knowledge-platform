from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, or_, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.invite import Invite
from app.models.referral import (
    ReferralChatMessage,
    ReferralChatMessageTranslation,
    ReferralChatThread,
    ReferralLink,
    ReferralProgressEvent,
)
from app.models.user import User
from app.schemas.referral import ReferralMeResponse
from app.schemas.referral_intelligence import (
    AgentMemoryContextInput,
    CreateCustomizedReferralLinkRequest,
    CreateReferralLinkRequest,
    ReferralChatMessageResponse,
    ReferralChatThreadSummaryResponse,
    ReferralDashboardStatsResponse,
    ReferralLinkSummaryResponse,
    ReferralLinksListResponse,
    ReferralProgressEventResponse,
    ReferralProgressEventsResponse,
    ReferralTranslationMetadata,
    RecordReferralWalletConnectionRequest,
    SendReferralChatMessageRequest,
    SyncPersonalizationToMemoryRequest,
    SyncPersonalizationToMemoryResponse,
    TranslateReferralChatMessageRequest,
    TranslateReferralChatMessageResponse,
    UpdateReferralLinkRequest,
)
from app.services.referral_intelligence_service import (
    ReferralChatParticipantMismatchError,
    ReferralChatUnavailableError,
    ReferralIntelligenceDomainError,
    ReferralIntelligenceService,
    ReferralLinkNotFoundError,
)

router = APIRouter(prefix="/referrals", tags=["referrals"])


def _invite_link(code: str) -> str:
    return f"https://example.invalid/register?invite={code}"


def _invite_for_user(user: User):
    normalized_email = user.email.strip().lower()
    now = datetime.now(timezone.utc)
    return (
        select(Invite)
        .where(
            Invite.is_active.is_(True),
            Invite.is_used.is_(False),
            or_(Invite.expires_at.is_(None), Invite.expires_at >= now),
            or_(
                Invite.email == user.email,
                Invite.email == normalized_email,
            ),
        )
        .order_by(
            desc(Invite.email == user.email),
            desc(Invite.email == normalized_email),
            desc(Invite.created_at),
        )
        .limit(1)
    )


def _service() -> ReferralIntelligenceService:
    return ReferralIntelligenceService()


def _to_translation_metadata(translation: ReferralChatMessageTranslation | None) -> ReferralTranslationMetadata | None:
    if translation is None:
        return None
    return ReferralTranslationMetadata(
        source_language=translation.source_locale,
        target_language=translation.target_locale,
        provider=translation.provider,
        confidence=translation.confidence,
        translated_at=translation.created_at,
    )


def _delivery_status_for_viewer(message: ReferralChatMessage, viewer_role: str) -> str:
    if message.sender_role != viewer_role:
        return "read"
    if viewer_role == "referrer":
        return "read" if message.is_read_by_invitee else "delivered"
    if viewer_role == "invitee":
        return "read" if message.is_read_by_owner else "delivered"
    return "sent"


def _translation_for_viewer(
    message: ReferralChatMessage,
    viewer_locale: str | None,
) -> ReferralChatMessageTranslation | None:
    if viewer_locale is None:
        return None
    normalized_locale = viewer_locale.strip().lower().replace("_", "-").split("-", 1)[0]
    for translation in message.translations or []:
        if translation.target_locale == normalized_locale:
            return translation
    return None


def _to_chat_message_response(
    message: ReferralChatMessage,
    viewer_role: str,
    viewer_locale: str | None,
) -> ReferralChatMessageResponse:
    original_locale = message.source_language or "auto"
    translation = _translation_for_viewer(message, viewer_locale)
    translated_text = translation.translated_text if translation is not None else None
    return ReferralChatMessageResponse(
        id=message.id,
        thread_id=message.thread_id,
        referral_link_id=message.referral_link_id,
        sender_role=message.sender_role,
        body=message.body,
        original_text=message.body,
        original_locale=original_locale,
        source_language=message.source_language,
        translated_text=translated_text,
        translated_text_for_viewer=translated_text,
        translation=_to_translation_metadata(translation),
        delivery_status=_delivery_status_for_viewer(message, viewer_role),
        metadata=message.metadata_json,
        is_read_by_owner=message.is_read_by_owner,
        is_read_by_invitee=message.is_read_by_invitee,
        created_at=message.created_at,
    )


def _unread_count_for_viewer(messages: list[ReferralChatMessage], viewer_role: str) -> int:
    if viewer_role == "referrer":
        return sum(1 for item in messages if not item.is_read_by_owner and item.sender_role != "referrer")
    if viewer_role == "invitee":
        return sum(1 for item in messages if not item.is_read_by_invitee and item.sender_role != "invitee")
    return 0


def _to_chat_thread_summary(
    thread: ReferralChatThread,
    viewer_role: str,
    viewer_locale: str | None = None,
) -> ReferralChatThreadSummaryResponse:
    messages = list(thread.messages or [])
    unread_count = _unread_count_for_viewer(messages, viewer_role)
    return ReferralChatThreadSummaryResponse(
        id=thread.id,
        referral_link_id=thread.referral_link_id,
        owner_user_id=thread.owner_user_id,
        invitee_display_name=thread.invitee_display_name,
        invitee_wallet_address=thread.invitee_wallet_address,
        latest_message_at=thread.latest_message_at,
        unread_message_count=unread_count,
        current_user_role=viewer_role,
        messages=[_to_chat_message_response(item, viewer_role, viewer_locale) for item in messages],
    )


def _to_progress_event_response(event: ReferralProgressEvent) -> ReferralProgressEventResponse:
    return ReferralProgressEventResponse(
        id=event.id,
        referral_link_id=event.referral_link_id,
        status=event.status,
        title=event.title,
        description=event.description,
        occurred_at=event.occurred_at,
        metadata=event.metadata_json,
    )


def _to_link_summary(link: ReferralLink) -> ReferralLinkSummaryResponse:
    messages = list(link.chat_thread.messages if link.chat_thread and link.chat_thread.messages else [])
    unread_count = sum(1 for item in messages if not item.is_read_by_owner and item.sender_role != "referrer")
    return ReferralLinkSummaryResponse(
        id=link.id,
        owner_user_id=link.owner_user_id,
        invite_code=link.invite_code,
        short_url=link.short_url,
        label=link.label,
        color=link.color,
        is_customized=link.is_customized,
        created_at=link.created_at,
        latest_status=link.latest_status,
        unread_message_count=unread_count,
        chat_enabled=link.chat_enabled,
        progress_percent=link.progress_percent,
    )


def _raise_http_from_domain(exc: ReferralIntelligenceDomainError) -> HTTPException:
    if isinstance(exc, ReferralLinkNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ReferralChatUnavailableError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, ReferralChatParticipantMismatchError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _storage_unavailable_http_exception(exc: ProgrammingError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Referral storage is not initialized. Apply database migrations.",
    )


@router.get("/me", response_model=ReferralMeResponse)
def get_my_referral(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralMeResponse:
    try:
        invite = db.scalar(_invite_for_user(current_user))
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Referral storage is not initialized. Apply database migrations.",
        ) from exc
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral data is not available for this user",
        )
    return ReferralMeResponse(
        code=invite.code,
        invite_link=_invite_link(invite.code),
        total_referrals=None,
        total_rewards=None,
    )


@router.get("/dashboard-stats", response_model=ReferralDashboardStatsResponse)
def get_referral_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralDashboardStatsResponse:
    service = _service()
    try:
        stats = service.get_dashboard_stats(db, current_user.id)
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc
    return ReferralDashboardStatsResponse(
        total_invites=stats["total_invites"],
        activated_qora=stats["activated_qora"],
        first_microtask=stats["first_microtask"],
        first_achievement=stats["first_achievement"],
    )


@router.get("/links", response_model=ReferralLinksListResponse)
def get_referral_links(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralLinksListResponse:
    service = _service()
    try:
        links = service.list_links(db, current_user.id)
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc
    return ReferralLinksListResponse(links=[_to_link_summary(link) for link in links])


@router.post("/links", response_model=ReferralLinkSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_referral_link(
    payload: CreateReferralLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralLinkSummaryResponse:
    service = _service()
    try:
        link = service.create_regular_link(
            db,
            owner_user_id=current_user.id,
            label=payload.label,
            color=payload.color,
        )
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc
    return _to_link_summary(link)


@router.patch("/links/{referral_link_id}", response_model=ReferralLinkSummaryResponse)
def update_referral_link(
    referral_link_id: UUID,
    payload: UpdateReferralLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralLinkSummaryResponse:
    service = _service()
    try:
        link = service.update_link(
            db,
            owner_user_id=current_user.id,
            referral_link_id=referral_link_id,
            label=payload.label,
            color=payload.color,
        )
    except ReferralIntelligenceDomainError as exc:
        raise _raise_http_from_domain(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc
    return _to_link_summary(link)


@router.post("/links/customized", response_model=ReferralLinkSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_customized_referral_link(
    payload: CreateCustomizedReferralLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralLinkSummaryResponse:
    service = _service()
    try:
        link = service.create_customized_link(
            db,
            owner_user_id=current_user.id,
            label=payload.label,
            color=payload.color,
            personalization_profile=payload.personalization_profile,
        )
    except ReferralIntelligenceDomainError as exc:
        raise _raise_http_from_domain(exc) from exc
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc
    return _to_link_summary(link)


@router.get("/links/{referral_link_id}/progress-events", response_model=ReferralProgressEventsResponse)
def get_referral_progress_events(
    referral_link_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralProgressEventsResponse:
    service = _service()
    try:
        events = service.list_progress_events(
            db,
            owner_user_id=current_user.id,
            referral_link_id=referral_link_id,
        )
    except ReferralIntelligenceDomainError as exc:
        raise _raise_http_from_domain(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc
    return ReferralProgressEventsResponse(events=[_to_progress_event_response(item) for item in events])


@router.get("/agent-context/by-invite/{invite_code}", response_model=AgentMemoryContextInput)
def get_referral_agent_context_by_invite(
    invite_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentMemoryContextInput:
    service = _service()
    try:
        return service.get_agent_context_by_invite_code(
            db,
            invite_code=invite_code,
            current_user_id=current_user.id,
            metadata={"access_path": "referral_agent_context_endpoint"},
        )
    except ReferralIntelligenceDomainError as exc:
        raise _raise_http_from_domain(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc


@router.get("/links/{referral_link_id}/chat-thread", response_model=ReferralChatThreadSummaryResponse)
def get_referral_chat_thread(
    referral_link_id: UUID,
    viewer_locale: str | None = Query(default=None, min_length=1, max_length=16),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralChatThreadSummaryResponse:
    service = _service()
    try:
        thread, viewer_role = service.get_chat_thread(
            db,
            participant_user_id=current_user.id,
            referral_link_id=referral_link_id,
            viewer_locale=viewer_locale,
        )
    except ReferralIntelligenceDomainError as exc:
        raise _raise_http_from_domain(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc
    return _to_chat_thread_summary(thread, viewer_role, viewer_locale)


@router.post(
    "/links/{referral_link_id}/chat-thread/messages",
    response_model=ReferralChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_referral_chat_message(
    referral_link_id: UUID,
    payload: SendReferralChatMessageRequest,
    viewer_locale: str | None = Query(default=None, min_length=1, max_length=16),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralChatMessageResponse:
    service = _service()
    try:
        message = service.send_chat_message(
            db,
            participant_user_id=current_user.id,
            referral_link_id=referral_link_id,
            requested_sender_role=payload.sender_role,
            body=payload.message,
            source_language=payload.source_language or payload.original_locale,
            metadata=payload.metadata,
        )
    except ReferralIntelligenceDomainError as exc:
        raise _raise_http_from_domain(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc
    viewer_role = "referrer" if message.sender_role == "referrer" else "invitee"
    return _to_chat_message_response(message, viewer_role, viewer_locale or payload.original_locale or payload.source_language)


@router.post(
    "/links/{referral_link_id}/chat-thread/read",
    response_model=ReferralChatThreadSummaryResponse,
)
def mark_referral_chat_thread_read(
    referral_link_id: UUID,
    viewer_locale: str | None = Query(default=None, min_length=1, max_length=16),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralChatThreadSummaryResponse:
    service = _service()
    try:
        thread, viewer_role = service.mark_chat_thread_read(
            db,
            participant_user_id=current_user.id,
            referral_link_id=referral_link_id,
            viewer_locale=viewer_locale,
        )
    except ReferralIntelligenceDomainError as exc:
        raise _raise_http_from_domain(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc
    return _to_chat_thread_summary(thread, viewer_role, viewer_locale)


@router.post(
    "/links/{referral_link_id}/wallet-connection",
    response_model=ReferralLinkSummaryResponse,
)
def record_referral_wallet_connection(
    referral_link_id: UUID,
    payload: RecordReferralWalletConnectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReferralLinkSummaryResponse:
    service = _service()
    try:
        link = service.record_wallet_connection(
            db,
            participant_user_id=current_user.id,
            referral_link_id=referral_link_id,
            wallet_address=payload.wallet_address,
            invitee_display_name=payload.invitee_display_name,
        )
    except ReferralIntelligenceDomainError as exc:
        raise _raise_http_from_domain(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc
    return _to_link_summary(link)


@router.post(
    "/links/{referral_link_id}/chat-thread/translate",
    response_model=TranslateReferralChatMessageResponse,
)
def translate_referral_chat_message(
    referral_link_id: UUID,
    payload: TranslateReferralChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TranslateReferralChatMessageResponse:
    service = _service()
    try:
        message = service.translate_message(
            db,
            participant_user_id=current_user.id,
            referral_link_id=referral_link_id,
            message_id=payload.message_id,
            target_language=payload.target_language,
        )
    except ReferralIntelligenceDomainError as exc:
        raise _raise_http_from_domain(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc

    if message.translation_created_at is None or message.translation_provider is None or message.translated_text is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation pipeline did not return expected metadata",
        )

    translation = ReferralTranslationMetadata(
        source_language=message.source_language or "auto",
        target_language=message.target_language or payload.target_language,
        provider=message.translation_provider,
        confidence=message.translation_confidence,
        translated_at=message.translation_created_at,
    )
    return TranslateReferralChatMessageResponse(
        message_id=message.id,
        translated_text=message.translated_text,
        translation=translation,
    )


@router.post("/links/{referral_link_id}/sync-personalization", response_model=SyncPersonalizationToMemoryResponse)
def sync_personalization_to_memory(
    referral_link_id: UUID,
    payload: SyncPersonalizationToMemoryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SyncPersonalizationToMemoryResponse:
    if payload.referral_link_id != referral_link_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Referral link id mismatch between path and payload",
        )

    service = _service()
    try:
        enrichment_payload = service.sync_personalization_to_memory(
            db,
            owner_user_id=current_user.id,
            referral_link_id=payload.referral_link_id,
            metadata=payload.metadata,
        )
    except ReferralIntelligenceDomainError as exc:
        raise _raise_http_from_domain(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProgrammingError as exc:
        raise _storage_unavailable_http_exception(exc) from exc

    return SyncPersonalizationToMemoryResponse(
        synced=True,
        payload=enrichment_payload,
    )
