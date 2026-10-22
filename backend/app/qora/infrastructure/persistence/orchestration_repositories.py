from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.qora.domain.enums import PersonaCore, Section
from app.qora.infrastructure.persistence.models import (
    OrchestratorExecution,
    ProductCatalogItem,
    ProductPersonaWeight,
    ProductWeightTableVersion,
    QualificationAnswer,
)


class ExecutionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, *, user_id: UUID, conversation_id: UUID, request_id: str) -> OrchestratorExecution | None:
        return self.session.scalar(
            select(OrchestratorExecution).where(
                OrchestratorExecution.user_id == user_id,
                OrchestratorExecution.conversation_id == conversation_id,
                OrchestratorExecution.request_id == request_id,
            )
        )

    def create(self, execution: OrchestratorExecution) -> OrchestratorExecution:
        self.session.add(execution)
        self.session.flush()
        return execution

    def complete(self, execution: OrchestratorExecution, response: dict[str, Any], state_version: int) -> None:
        execution.status = "COMPLETED"
        execution.response_payload = response
        execution.state_version_after = state_version
        execution.updated_at = datetime.now(timezone.utc)
        self.session.flush()

    def fail(self, execution: OrchestratorExecution, error_code: str) -> None:
        execution.status = "FAILED"
        execution.error_code = error_code
        execution.updated_at = datetime.now(timezone.utc)
        self.session.flush()


class QualificationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_section(
        self, *, user_id: UUID, conversation_id: UUID, section: Section
    ) -> list[QualificationAnswer]:
        return list(
            self.session.scalars(
                select(QualificationAnswer)
                .where(
                    QualificationAnswer.user_id == user_id,
                    QualificationAnswer.conversation_id == conversation_id,
                    QualificationAnswer.section == section.value,
                )
                .order_by(QualificationAnswer.asked_at.asc())
            ).all()
        )

    def pending(self, *, user_id: UUID, conversation_id: UUID, section: Section) -> QualificationAnswer | None:
        return self.session.scalar(
            select(QualificationAnswer)
            .where(
                QualificationAnswer.user_id == user_id,
                QualificationAnswer.conversation_id == conversation_id,
                QualificationAnswer.section == section.value,
                QualificationAnswer.status == "ASKED",
            )
            .order_by(QualificationAnswer.asked_at.asc())
            .limit(1)
        )

    def ask(self, answer: QualificationAnswer) -> QualificationAnswer:
        self.session.add(answer)
        self.session.flush()
        return answer

    def answer(self, record: QualificationAnswer, value: dict[str, Any], confidence: float, request_id: str) -> None:
        record.answer_value = value
        record.confidence = confidence
        record.status = "ANSWERED"
        record.request_id = request_id
        record.answered_at = datetime.now(timezone.utc)
        self.session.flush()


class ProductPolicyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def active_version(self, now: datetime | None = None) -> ProductWeightTableVersion | None:
        effective_now = now or datetime.now(timezone.utc)
        return self.session.scalar(
            select(ProductWeightTableVersion)
            .where(
                ProductWeightTableVersion.status == "ACTIVE",
                ProductWeightTableVersion.effective_from <= effective_now,
                (
                    ProductWeightTableVersion.effective_to.is_(None)
                    | (ProductWeightTableVersion.effective_to > effective_now)
                ),
            )
            .order_by(ProductWeightTableVersion.effective_from.desc())
            .limit(1)
        )

    def products_for_section(self, section: Section) -> list[ProductCatalogItem]:
        return list(
            self.session.scalars(
                select(ProductCatalogItem)
                .where(ProductCatalogItem.section == section.value)
                .order_by(ProductCatalogItem.product_id.asc())
            ).all()
        )

    def weights(
        self, *, version_id: UUID, section: Section, persona: PersonaCore
    ) -> dict[str, float]:
        rows = self.session.execute(
            select(ProductPersonaWeight.product_id, ProductPersonaWeight.weight)
            .join(ProductCatalogItem, ProductCatalogItem.product_id == ProductPersonaWeight.product_id)
            .where(
                ProductPersonaWeight.table_version_id == version_id,
                ProductPersonaWeight.persona_core == persona.value,
                ProductCatalogItem.section == section.value,
            )
        ).all()
        return {product_id: float(weight) for product_id, weight in rows}

