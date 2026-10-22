from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.qora.config import QoraPolicyConfig, load_qora_policy
from app.qora.domain.achievement import (
    AchievementCandidate,
    AchievementContext,
    AchievementDecision,
    AchievementEngine,
    LevelCard,
)
from app.qora.domain.enums import (
    AchievementStatus,
    DefinitionStatus,
    PersonaCore,
    PersonaModifier,
    PointSourceType,
    QoraEventType,
    Section,
)
from app.qora.infrastructure.persistence.models import (
    AchievementDefinition,
    AchievementPointLedger,
    AgentUserState,
    LevelDefinition,
    ReferralReward,
    ReferralRuleDefinition,
    UserAchievement,
    UserInteractionEvent,
)


class AchievementCompletionResult(BaseModel):
    achievement_id: str
    points_awarded: int
    current_points: int
    current_level: int
    level_up: bool
    referral_reward_points: int = 0
    idempotent_replay: bool = False


class AchievementCompletionError(ValueError):
    pass


class AchievementService:
    """Transactional achievement access point and deterministic progress policy."""

    def __init__(self, session: Session, policy: QoraPolicyConfig | None = None) -> None:
        self.session = session
        self.policy = policy or load_qora_policy()
        self.engine = AchievementEngine(
            readiness_threshold=self.policy.achievement.readiness_threshold
        )

    def get_next_best_achievement(self, user_state: AgentUserState) -> AchievementDecision:
        now = datetime.now(timezone.utc)
        candidates = list(
            self.session.scalars(
                select(AchievementDefinition)
                .where(
                    AchievementDefinition.status == DefinitionStatus.ACTIVE.value,
                    AchievementDefinition.valid_from <= now,
                    (
                        AchievementDefinition.valid_to.is_(None)
                        | (AchievementDefinition.valid_to > now)
                    ),
                )
                .order_by(AchievementDefinition.code, AchievementDefinition.version.desc())
            ).all()
        )
        completed_ids = set(
            self.session.scalars(
                select(UserAchievement.achievement_id).where(
                    UserAchievement.user_id == user_state.user_id,
                    UserAchievement.status == AchievementStatus.COMPLETED.value,
                )
            ).all()
        )
        next_level = self._next_level(user_state.current_level)
        return self.engine.get_next_best_achievement(
            persona_core=PersonaCore(user_state.persona_core) if user_state.persona_core else None,
            persona_modifiers=[PersonaModifier(value) for value in user_state.persona_modifiers],
            intent=user_state.current_intent,
            selected_section=Section(user_state.selected_section) if user_state.selected_section else None,
            matched_product=self._matched_product_id(user_state),
            current_points=user_state.current_points,
            current_level=user_state.current_level,
            readiness_score=user_state.readiness_score,
            completed_achievement_ids=completed_ids,
            candidates=[self._candidate(row) for row in candidates],
            next_level_threshold=next_level.minimum_points if next_level else None,
        )

    def level_card(
        self,
        user_state: AgentUserState,
        achievement: AchievementContext | None = None,
    ) -> LevelCard:
        next_level = self._next_level(user_state.current_level)
        return self.engine.level_card(
            current_level=user_state.current_level,
            current_points=user_state.current_points,
            next_level=next_level.level if next_level else None,
            next_level_threshold=next_level.minimum_points if next_level else None,
            reward_token=achievement.expected_reward_hint if achievement else None,
            task_label=achievement.micro_task.label if achievement else None,
            estimated_points_gain=achievement.estimated_points_gain if achievement else 0,
        )

    def start_achievement(
        self,
        *,
        user_id: UUID,
        achievement_id: UUID,
        conversation_id: UUID,
        request_id: str,
        idempotency_key: str,
    ) -> UserAchievement:
        existing = self.session.scalar(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id,
            )
        )
        if existing:
            return existing
        row = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            status=AchievementStatus.STARTED.value,
            progress={"confirmed_actions": []},
            points_awarded=0,
            started_at=datetime.now(timezone.utc),
            idempotency_key=idempotency_key,
        )
        try:
            self.session.add(row)
            self._append_event(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=QoraEventType.ACHIEVEMENT_STARTED.value,
                entity_id=str(achievement_id),
                request_id=request_id,
                idempotency_key=f"achievement-start:{idempotency_key}",
                metadata={},
            )
            self.session.commit()
            return row
        except IntegrityError:
            self.session.rollback()
            duplicate = self.session.scalar(
                select(UserAchievement).where(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement_id,
                )
            )
            if duplicate is None:
                raise
            return duplicate
        except Exception:
            self.session.rollback()
            raise

    def complete_achievement(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        achievement_id: UUID,
        confirmation_event_type: str,
        request_id: str,
        idempotency_key: str,
        referrer_user_id: UUID | None = None,
    ) -> AchievementCompletionResult:
        if confirmation_event_type not in self.policy.achievement.completion_event_types:
            raise AchievementCompletionError("Completion requires a configured backend confirmation event")
        replay = self.session.scalar(
            select(AchievementPointLedger).where(
                AchievementPointLedger.user_id == user_id,
                AchievementPointLedger.idempotency_key == idempotency_key,
            )
        )
        if replay:
            state = self._state(user_id, conversation_id)
            return AchievementCompletionResult(
                achievement_id=str(achievement_id),
                points_awarded=replay.points,
                current_points=state.current_points,
                current_level=state.current_level,
                level_up=False,
                idempotent_replay=True,
            )

        try:
            state = self.session.scalar(
                select(AgentUserState)
                .where(
                    AgentUserState.user_id == user_id,
                    AgentUserState.conversation_id == conversation_id,
                )
                .with_for_update()
            )
            if state is None:
                raise AchievementCompletionError("QORA state was not found")
            definition = self.session.scalar(
                select(AchievementDefinition).where(
                    AchievementDefinition.id == achievement_id,
                    AchievementDefinition.status == DefinitionStatus.ACTIVE.value,
                )
            )
            if definition is None:
                raise AchievementCompletionError("Achievement is not active")
            user_achievement = self.session.scalar(
                select(UserAchievement)
                .where(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement_id,
                )
                .with_for_update()
            )
            if user_achievement and user_achievement.status == AchievementStatus.COMPLETED.value:
                raise AchievementCompletionError("Achievement was already completed")

            old_level = state.current_level
            new_points = state.current_points + definition.points_reward
            new_level = self._level_for_points(new_points).level
            result = self.session.execute(
                update(AgentUserState)
                .where(AgentUserState.id == state.id, AgentUserState.version == state.version)
                .values(
                    current_points=new_points,
                    current_level=new_level,
                    version=state.version + 1,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            if result.rowcount != 1:
                raise AchievementCompletionError("State version conflict during achievement completion")

            if user_achievement is None:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement_id,
                    status=AchievementStatus.COMPLETED.value,
                    progress={"confirmed_actions": [confirmation_event_type]},
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    points_awarded=definition.points_reward,
                    idempotency_key=idempotency_key,
                )
                self.session.add(user_achievement)
            else:
                user_achievement.status = AchievementStatus.COMPLETED.value
                user_achievement.completed_at = datetime.now(timezone.utc)
                user_achievement.points_awarded = definition.points_reward
                user_achievement.idempotency_key = idempotency_key
                user_achievement.progress = {"confirmed_actions": [confirmation_event_type]}

            self.session.add(
                AchievementPointLedger(
                    user_id=user_id,
                    achievement_id=achievement_id,
                    points=definition.points_reward,
                    source_type=PointSourceType.PERSONAL_ACHIEVEMENT.value,
                    rule_version=definition.version,
                    idempotency_key=idempotency_key,
                )
            )
            self._append_event(
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=QoraEventType.ACHIEVEMENT_COMPLETED.value,
                entity_id=str(achievement_id),
                request_id=request_id,
                idempotency_key=f"achievement-complete:{idempotency_key}",
                metadata={"points": definition.points_reward, "rule_version": definition.version},
            )
            if new_level > old_level:
                self._append_event(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    event_type=QoraEventType.LEVEL_UP.value,
                    entity_id=str(new_level),
                    request_id=request_id,
                    idempotency_key=f"level-up:{idempotency_key}",
                    metadata={"from_level": old_level, "to_level": new_level},
                )
            referral_points = self._create_referral_reward(
                referrer_user_id=referrer_user_id,
                referred_state=state,
                achievement=definition,
                source_points=definition.points_reward,
                idempotency_key=idempotency_key,
            )
            self.session.commit()
            return AchievementCompletionResult(
                achievement_id=str(achievement_id),
                points_awarded=definition.points_reward,
                current_points=new_points,
                current_level=new_level,
                level_up=new_level > old_level,
                referral_reward_points=referral_points,
            )
        except IntegrityError as exc:
            self.session.rollback()
            replay = self.session.scalar(
                select(AchievementPointLedger).where(
                    AchievementPointLedger.user_id == user_id,
                    AchievementPointLedger.idempotency_key == idempotency_key,
                )
            )
            if replay:
                state = self._state(user_id, conversation_id)
                return AchievementCompletionResult(
                    achievement_id=str(achievement_id),
                    points_awarded=replay.points,
                    current_points=state.current_points,
                    current_level=state.current_level,
                    level_up=False,
                    idempotent_replay=True,
                )
            raise AchievementCompletionError("Concurrent or duplicate completion") from exc
        except Exception:
            self.session.rollback()
            raise

    def _create_referral_reward(
        self,
        *,
        referrer_user_id: UUID | None,
        referred_state: AgentUserState,
        achievement: AchievementDefinition,
        source_points: int,
        idempotency_key: str,
    ) -> int:
        if referrer_user_id is None or referrer_user_id == referred_state.user_id:
            return 0
        now = datetime.now(timezone.utc)
        rule = self.session.scalar(
            select(ReferralRuleDefinition).where(
                ReferralRuleDefinition.version == self.policy.achievement.referral_rule_version,
                ReferralRuleDefinition.status == DefinitionStatus.ACTIVE.value,
                ReferralRuleDefinition.effective_from <= now,
                (
                    ReferralRuleDefinition.effective_to.is_(None)
                    | (ReferralRuleDefinition.effective_to > now)
                ),
            )
        )
        if rule is None:
            return 0
        referrer_state = self.session.scalar(
            select(AgentUserState)
            .where(AgentUserState.user_id == referrer_user_id)
            .order_by(AgentUserState.updated_at.desc())
            .limit(1)
        )
        eligible = bool(
            referrer_state
            and (
                not rule.same_level_or_below_only
                or referred_state.current_level <= referrer_state.current_level
            )
        )
        reason = "SAME_OR_BELOW_LEVEL" if eligible else "REFERRED_LEVEL_ABOVE_REFERRER"
        # Conservative floor prevents fractional or over-awarded points.
        reward_points = int(source_points * rule.reward_percentage) if eligible else 0
        self.session.add(
            ReferralReward(
                referrer_user_id=referrer_user_id,
                referred_user_id=referred_state.user_id,
                source_achievement_id=achievement.id,
                source_points=source_points,
                reward_percentage=rule.reward_percentage,
                reward_points=reward_points,
                eligible=eligible,
                reason=reason,
                rule_version=rule.version,
                idempotency_key=f"referral:{idempotency_key}",
            )
        )
        return reward_points

    def _next_level(self, current_level: int) -> LevelDefinition | None:
        return self.session.scalar(
            select(LevelDefinition)
            .where(
                LevelDefinition.status == DefinitionStatus.ACTIVE.value,
                LevelDefinition.level > current_level,
            )
            .order_by(LevelDefinition.level)
            .limit(1)
        )

    def _level_for_points(self, points: int) -> LevelDefinition:
        row = self.session.scalar(
            select(LevelDefinition)
            .where(
                LevelDefinition.status == DefinitionStatus.ACTIVE.value,
                LevelDefinition.minimum_points <= points,
                (LevelDefinition.maximum_points.is_(None) | (LevelDefinition.maximum_points >= points)),
            )
            .order_by(LevelDefinition.level.desc())
            .limit(1)
        )
        if row is None:
            raise AchievementCompletionError("No active level definition covers the resulting points")
        return row

    def _state(self, user_id: UUID, conversation_id: UUID) -> AgentUserState:
        state = self.session.scalar(
            select(AgentUserState).where(
                AgentUserState.user_id == user_id,
                AgentUserState.conversation_id == conversation_id,
            )
        )
        if state is None:
            raise AchievementCompletionError("QORA state was not found")
        return state

    @staticmethod
    def _matched_product_id(state: AgentUserState) -> str | None:
        return str(state.matched_product.get("product_id")) if state.matched_product else None

    @staticmethod
    def _candidate(row: AchievementDefinition) -> AchievementCandidate:
        return AchievementCandidate(
            id=row.id,
            code=row.code,
            title=row.title,
            section=row.section,
            product_id=row.product_id,
            eligible_personas=tuple(row.eligible_personas),
            eligible_levels=tuple(row.eligible_levels),
            required_actions=tuple(row.required_actions),
            points_reward=row.points_reward,
            reward_token=row.reward_token,
            prerequisites=tuple(row.prerequisites),
        )

    def _append_event(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        event_type: str,
        entity_id: str,
        request_id: str,
        idempotency_key: str,
        metadata: dict,
    ) -> None:
        self.session.add(
            UserInteractionEvent(
                event_id=f"evt_{uuid4().hex}",
                user_id=user_id,
                conversation_id=conversation_id,
                event_type=event_type,
                entity_type="ACHIEVEMENT",
                entity_id=entity_id,
                metadata_json=metadata,
                occurred_at=datetime.now(timezone.utc),
                request_id=request_id,
                idempotency_key=idempotency_key,
            )
        )
