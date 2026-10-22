"""Non-blocking persistence logger for conversion outcomes and trigger analytics."""

from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.analytics.repositories import ConversionAnalyticsRepository, TriggerEffectivenessRepository
from app.core.database import SessionLocal
from app.internal.conversion.enums import FunnelStage, TriggerType
from app.observability.models import ConversionEvent as ConversionOutcomeEvent

logger = logging.getLogger(__name__)


class OutcomeLogger:
    """Persist conversion outcomes without blocking dialogue response flow."""

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal
        self._disabled = False
        self._disabled_reason: str | None = None

    def log_conversion_outcome(self, event: ConversionOutcomeEvent) -> None:
        """Persist one conversion outcome event and update trigger effectiveness snapshot."""
        if self._disabled:
            logger.debug(
                "outcome_logger.skipped_disabled session_id=%s reason=%s",
                event.session_id,
                self._disabled_reason or "disabled",
            )
            return

        db = self._session_factory()
        try:
            conversion_repo = ConversionAnalyticsRepository(db)
            trigger_repo = TriggerEffectivenessRepository(db)

            primary_trigger = self._resolve_primary_trigger(event)
            secondary_trigger = self._resolve_secondary_trigger(event)
            stage = self._resolve_funnel_stage(event.stage)

            conversion_repo.create(
                {
                    "user_id": event.user_id,
                    "session_id": event.session_id,
                    "event_type": primary_trigger,
                    "stage": stage,
                    "persona_type": None,
                    "persona": event.persona,
                    "confidence": event.confidence,
                    "trust_score": event.trust_score,
                    "engagement_score": event.engagement_score,
                    "triggers_used": [trigger.value for trigger in event.triggers_used],
                    "cta_type": event.cta_type.value if event.cta_type is not None else None,
                    "cta_strength": event.cta_strength.value,
                    "outcome": event.outcome.value,
                    "cta_outcome": event.cta_outcome.value if event.cta_outcome is not None else None,
                    "experiment_name": str(event.metadata.get("experiment_name")) if event.metadata.get("experiment_name") else None,
                    "experiment_variant": event.experiment_variant,
                    "metadata_json": event.metadata,
                    "source": "outcome_logger",
                    "created_at": event.timestamp,
                }
            )

            key_payload = {
                "trigger_primary": primary_trigger.value,
                "trigger_secondary": secondary_trigger.value if secondary_trigger is not None else None,
                "persona": event.persona,
                "stage": event.stage,
            }
            existing = trigger_repo.trigger_performance_by_stage(event.stage)
            target = next(
                (
                    item
                    for item in existing
                    if item.trigger_primary == key_payload["trigger_primary"]
                    and item.trigger_secondary == key_payload["trigger_secondary"]
                    and item.persona == key_payload["persona"]
                ),
                None,
            )
            success = 1 if event.outcome.value in {"economic_action_ready", "stage_advanced"} else 0

            if target is None:
                trigger_repo.create(
                    {
                        **key_payload,
                        "success_rate": float(success),
                        "sample_size": 1,
                    }
                )
            else:
                next_sample_size = target.sample_size + 1
                cumulative = (target.success_rate * target.sample_size) + success
                trigger_repo.upsert_by_signature(
                    {
                        **key_payload,
                        "success_rate": cumulative / next_sample_size,
                        "sample_size": next_sample_size,
                    }
                )

            db.commit()
        except (OperationalError, ProgrammingError) as exc:
            db.rollback()
            if self._is_schema_unavailable_error(exc):
                self._disabled = True
                self._disabled_reason = "analytics_schema_unavailable"
                logger.warning(
                    "outcome_logger.disabled reason=%s session_id=%s",
                    self._disabled_reason,
                    event.session_id,
                )
                return
            logger.warning("outcome_logger.persist_failed session_id=%s", event.session_id, exc_info=True)
        except Exception:
            db.rollback()
            logger.warning("outcome_logger.persist_failed session_id=%s", event.session_id, exc_info=True)
        finally:
            db.close()

    @staticmethod
    def _is_schema_unavailable_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return (
            "no such table" in message
            or "does not exist" in message
            or "undefined table" in message
            or "relation" in message and "does not exist" in message
        )

    @staticmethod
    def _resolve_primary_trigger(event: ConversionOutcomeEvent) -> TriggerType:
        if event.triggers_used:
            return OutcomeLogger._map_trigger(event.triggers_used[0].value)
        return TriggerType.EDUCATIONAL_NUDGE

    @staticmethod
    def _resolve_secondary_trigger(event: ConversionOutcomeEvent) -> TriggerType | None:
        if len(event.triggers_used) < 2:
            return None
        return OutcomeLogger._map_trigger(event.triggers_used[1].value)

    @staticmethod
    def _resolve_funnel_stage(value: str) -> FunnelStage:
        token = str(value).strip().lower()
        mapping = {
            "entry": FunnelStage.AWARENESS,
            "exploration": FunnelStage.AWARENESS,
            "trust_formation": FunnelStage.CONSIDERATION,
            "opportunity_awareness": FunnelStage.INTENT,
            "micro_commitment": FunnelStage.DECISION,
            "economic_action": FunnelStage.CONVERSION,
            "awareness": FunnelStage.AWARENESS,
            "consideration": FunnelStage.CONSIDERATION,
            "intent": FunnelStage.INTENT,
            "decision": FunnelStage.DECISION,
            "conversion": FunnelStage.CONVERSION,
        }
        return mapping.get(token, FunnelStage.AWARENESS)

    @staticmethod
    def _map_trigger(value: str) -> TriggerType:
        token = str(value).strip().lower()
        mapping = {
            "social_proof": TriggerType.SOCIAL_PROOF,
            "scarcity": TriggerType.URGENCY_PROMPT,
            "authority": TriggerType.SOCIAL_PROOF,
            "transparency": TriggerType.EDUCATIONAL_NUDGE,
            "curiosity": TriggerType.EDUCATIONAL_NUDGE,
            "control": TriggerType.EDUCATIONAL_NUDGE,
            "loss_avoidance": TriggerType.URGENCY_PROMPT,
            "opportunity_framing": TriggerType.CTA_OFFER,
            "micro_commitment": TriggerType.CTA_OFFER,
            "future_self": TriggerType.EDUCATIONAL_NUDGE,
            "educational_nudge": TriggerType.EDUCATIONAL_NUDGE,
            "urgency_prompt": TriggerType.URGENCY_PROMPT,
            "cta_offer": TriggerType.CTA_OFFER,
        }
        return mapping.get(token, TriggerType.EDUCATIONAL_NUDGE)
