from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID

from pydantic import BaseModel, Field

from app.qora.domain.enums import PersonaCore, PersonaModifier, Section


class AchievementCTA(BaseModel):
    type: str
    label: str


class MicroTask(BaseModel):
    id: str
    label: str


class AchievementContext(BaseModel):
    achievement_id: str
    micro_task: MicroTask
    estimated_points_gain: int = Field(ge=0)
    level_progress_delta: float = Field(ge=0.0, le=1.0)
    expected_reward_hint: str | None = None
    explanation_style: str
    cta: AchievementCTA
    reason_codes: list[str] = Field(default_factory=list)


class LevelCard(BaseModel):
    current_level: int = Field(ge=1)
    current_points: int = Field(ge=0)
    next_level: int | None = None
    next_level_threshold: int | None = None
    points_needed: int = Field(ge=0)
    reward_token: str | None = None
    task_label: str | None = None
    estimated_points_gain: int = Field(ge=0)
    progress_percent: float = Field(ge=0.0, le=100.0)
    progress_hint: str


@dataclass(frozen=True, slots=True)
class AchievementCandidate:
    id: UUID
    code: str
    title: str
    section: str | None
    product_id: str | None
    eligible_personas: tuple[str, ...]
    eligible_levels: tuple[int, ...]
    required_actions: tuple[dict[str, Any], ...]
    points_reward: int
    reward_token: str | None
    prerequisites: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AchievementDecision:
    eligible: bool
    context: AchievementContext | None
    reason_codes: tuple[str, ...]


class AchievementEngine:
    """Pure deterministic policy. It never invents achievements or reward values."""

    def __init__(self, *, readiness_threshold: float) -> None:
        self.readiness_threshold = readiness_threshold

    def get_next_best_achievement(
        self,
        *,
        persona_core: PersonaCore | None,
        persona_modifiers: Iterable[PersonaModifier],
        intent: str | None,
        selected_section: Section | None,
        matched_product: str | None,
        current_points: int,
        current_level: int,
        readiness_score: float,
        completed_achievement_ids: set[UUID],
        candidates: Iterable[AchievementCandidate],
        next_level_threshold: int | None,
    ) -> AchievementDecision:
        missing = []
        if persona_core is None:
            missing.append("PERSONA_NOT_ESTABLISHED")
        if not intent:
            missing.append("INTENT_NOT_ESTABLISHED")
        if selected_section is None:
            missing.append("SECTION_NOT_SELECTED")
        if not matched_product:
            missing.append("PATH_NOT_SELECTED")
        if readiness_score < self.readiness_threshold:
            missing.append("READINESS_BELOW_THRESHOLD")
        if missing:
            return AchievementDecision(False, None, tuple(missing))

        eligible = [
            item for item in candidates
            if item.id not in completed_achievement_ids
            and (item.section is None or item.section == selected_section.value)
            and (item.product_id is None or item.product_id == matched_product)
            and (not item.eligible_personas or persona_core.value in item.eligible_personas)
            and (not item.eligible_levels or current_level in item.eligible_levels)
            and item.required_actions
        ]
        if not eligible:
            return AchievementDecision(False, None, ("NO_CONFIGURED_ELIGIBLE_ACHIEVEMENT",))

        # Narrower scope wins, then lower effort/points. The ordering is stable and explainable.
        eligible.sort(
            key=lambda item: (
                -(2 if item.product_id else 0) - (1 if item.section else 0),
                item.points_reward,
                item.code,
            )
        )
        selected = eligible[0]
        task = selected.required_actions[0]
        task_id = str(task.get("id") or task.get("code") or selected.code)
        task_label = str(task.get("label") or selected.title)
        denominator = max((next_level_threshold or current_points) - current_points, 1)
        progress_delta = min(selected.points_reward / denominator, 1.0)
        context = AchievementContext(
            achievement_id=str(selected.id),
            micro_task=MicroTask(id=task_id, label=task_label),
            estimated_points_gain=selected.points_reward,
            level_progress_delta=round(progress_delta, 4),
            expected_reward_hint=selected.reward_token,
            explanation_style=self._framing(persona_core),
            cta=AchievementCTA(type="START_MICRO_TASK", label="ادامه مسیر"),
            reason_codes=[
                "CONFIGURED_ACHIEVEMENT",
                "READINESS_CONFIRMED",
                "MATCHES_SELECTED_PATH",
            ],
        )
        return AchievementDecision(True, context, tuple(context.reason_codes))

    @staticmethod
    def level_card(
        *,
        current_level: int,
        current_points: int,
        next_level: int | None,
        next_level_threshold: int | None,
        reward_token: str | None,
        task_label: str | None,
        estimated_points_gain: int,
    ) -> LevelCard:
        if next_level_threshold is None:
            return LevelCard(
                current_level=current_level,
                current_points=current_points,
                points_needed=0,
                reward_token=reward_token,
                task_label=task_label,
                estimated_points_gain=estimated_points_gain,
                progress_percent=100.0,
                progress_hint="بالاترین Level فعال ثبت شده است",
            )
        points_needed = max(next_level_threshold - current_points, 0)
        progress_percent = round(min(current_points / max(next_level_threshold, 1), 1.0) * 100, 1)
        return LevelCard(
            current_level=current_level,
            current_points=current_points,
            next_level=next_level,
            next_level_threshold=next_level_threshold,
            points_needed=points_needed,
            reward_token=reward_token,
            task_label=task_label,
            estimated_points_gain=estimated_points_gain,
            progress_percent=progress_percent,
            progress_hint=f"{points_needed} points تا Level {next_level} باقی مانده است",
        )

    @staticmethod
    def _framing(persona: PersonaCore) -> str:
        return {
            PersonaCore.SAVER: "RULES_AND_FAIRNESS",
            PersonaCore.HUNTER: "EFFORT_TO_GAIN",
            PersonaCore.PLAYER: "PROGRESS_AND_UNLOCK",
            PersonaCore.ARCHITECT: "INCENTIVE_ARCHITECTURE",
        }[persona]
