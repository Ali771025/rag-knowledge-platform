from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.internal.conversion.orchestration_models import ConversionFunnelRequest
from app.internal.conversion.repositories.sqlalchemy import (
    SQLAlchemyConversionEventRepository,
    SQLAlchemyFunnelStateRepository,
)
from app.internal.conversion.service import ConversionFunnelService
from app.internal.persona.orchestration_models import PersonaIntelligenceRequest
from app.internal.persona.repositories.sqlalchemy import (
    SQLAlchemyModifierHistoryRepository,
    SQLAlchemyPersonaHistoryRepository,
    SQLAlchemyPersonaStateRepository,
)
from app.internal.persona.service import PersonaIntelligenceService
from app.internal.persona.transition_buffer_repository import RedisPersonaTransitionBufferRepository
from app.internal.persona.transition_manager import PersonaTransitionManager
from app.internal.policy.loader import load_default_policy_config
from app.schemas.persona_conversion import (
    ConversionUpdateApiRequest,
    ConversionUpdateApiResponse,
    PersonaAnalyzeApiRequest,
    PersonaAnalyzeApiResponse,
)

router = APIRouter(prefix="", tags=["persona-conversion"])
logger = logging.getLogger(__name__)


def _build_persona_service(db: Session) -> PersonaIntelligenceService:
    config = load_default_policy_config()
    buffer_store = RedisPersonaTransitionBufferRepository(
        ttl_seconds=1800,
        max_items=3,
    )
    transition_manager = PersonaTransitionManager(
        buffer_store=buffer_store,
        min_score_multiplier=config.persona.transition.min_score_multiplier,
        stability_window=config.persona.transition.stability_window,
        trust_low_speed_penalty=config.persona.transition.trust_low_speed_penalty,
    )
    return PersonaIntelligenceService(
        transition_manager=transition_manager,
        state_repository=SQLAlchemyPersonaStateRepository(db),
        history_repository=SQLAlchemyPersonaHistoryRepository(db),
        modifier_history_repository=SQLAlchemyModifierHistoryRepository(db),
        policy_config=config,
    )


def _build_conversion_service(db: Session) -> ConversionFunnelService:
    return ConversionFunnelService(
        funnel_state_repository=SQLAlchemyFunnelStateRepository(db),
        conversion_event_repository=SQLAlchemyConversionEventRepository(db),
        policy_config=load_default_policy_config(),
    )


@router.post("/persona/analyze", response_model=PersonaAnalyzeApiResponse)
async def analyze_persona(
    payload: PersonaAnalyzeApiRequest,
    db: Session = Depends(get_db),
) -> PersonaAnalyzeApiResponse:
    service = _build_persona_service(db)
    try:
        result = await service.analyze(
            PersonaIntelligenceRequest(
                session_id=payload.session_id,
                user_id=payload.user_id,
                message=payload.message,
                metadata=payload.metadata,
                recent_messages=payload.recent_messages,
                current_persona=payload.current_persona,
            )
        )
        db.commit()
        return PersonaAnalyzeApiResponse.model_validate(result.model_dump(mode="json"))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive fallback
        db.rollback()
        logger.exception("persona.analyze_failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Persona analysis failed") from exc


@router.post("/conversion/update", response_model=ConversionUpdateApiResponse)
async def update_conversion(
    payload: ConversionUpdateApiRequest,
    db: Session = Depends(get_db),
) -> ConversionUpdateApiResponse:
    service = _build_conversion_service(db)
    try:
        result = await service.update(
            ConversionFunnelRequest(
                session_id=payload.session_id,
                user_id=payload.user_id,
                persona_label=payload.persona_label,
                persona_confidence=payload.persona_confidence,
                trust_score=payload.trust_score,
                current_stage=payload.current_stage,
                intent=payload.intent,
                is_ambiguous=payload.is_ambiguous,
                repeated_interaction_count=payload.repeated_interaction_count,
                clarification_success_count=payload.clarification_success_count,
                objection_count=payload.objection_count,
                confusion_count=payload.confusion_count,
                metadata=payload.metadata,
            )
        )
        db.commit()
        return ConversionUpdateApiResponse.model_validate(result.model_dump(mode="json"))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive fallback
        db.rollback()
        logger.exception("conversion.update_failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Conversion update failed") from exc
