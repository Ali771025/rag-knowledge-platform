from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.qora.domain.enums import Section
from app.qora.domain.product_ranking import DEFAULT_PRODUCT_WEIGHTS
from app.qora.domain.routing import PRODUCT_SECTIONS
from app.qora.infrastructure.persistence.models import (
    LevelDefinition,
    ProductCatalogItem,
    ProductPersonaWeight,
    ProductWeightTableVersion,
    ReferralRuleDefinition,
)


def seed_default_product_policy(
    session: Session,
    *,
    version: str = "qora-product-weights-v1",
    rag_ready: bool = False,
    compliance_flag: str = "REVIEW",
) -> ProductWeightTableVersion:
    """Idempotent bootstrap for tests/dev; production uses the Alembic seed."""
    existing = session.query(ProductWeightTableVersion).filter_by(weight_table_version=version).one_or_none()
    if existing is not None:
        return existing
    now = datetime.now(timezone.utc)
    table_version = ProductWeightTableVersion(
        weight_table_version=version,
        effective_from=now,
        created_by="qora-bootstrap",
        approved_by="qora-bootstrap",
        status="ACTIVE",
    )
    session.add(table_version)
    session.flush()
    for product_id, weights in DEFAULT_PRODUCT_WEIGHTS.items():
        item = ProductCatalogItem(
            product_id=product_id,
            section=PRODUCT_SECTIONS[product_id].value,
            display_name=product_id.replace("_", " ").title(),
            is_active=True,
            rag_ready=rag_ready,
            compliance_flag=compliance_flag,
            restrictions={},
            metadata_json={},
        )
        session.add(item)
        session.flush()
        for persona, weight in weights.items():
            session.add(
                ProductPersonaWeight(
                    table_version_id=table_version.id,
                    product_id=product_id,
                    persona_core=persona.value,
                    weight=weight,
                )
            )
    session.commit()
    return table_version


def seed_default_achievement_policy(session: Session) -> None:
    """Seed only documented level/referral rules; achievements require approved definitions."""
    if session.get(LevelDefinition, 1) is None:
        session.add_all([
            LevelDefinition(
                level=1,
                minimum_points=0,
                maximum_points=249,
                title="Level 1",
                unlock_rules={
                    "document_threshold": 100,
                    "threshold_semantics": "INTERIM_MILESTONE",
                },
                status="ACTIVE",
            ),
            LevelDefinition(
                level=2,
                minimum_points=250,
                maximum_points=None,
                title="Level 2",
                unlock_rules={
                    "document_threshold": 250,
                    "threshold_semantics": "CUMULATIVE",
                },
                status="ACTIVE",
            ),
        ])
    if session.get(ReferralRuleDefinition, "qora-referral-v1") is None:
        session.add(
            ReferralRuleDefinition(
                version="qora-referral-v1",
                reward_percentage=0.10,
                same_level_or_below_only=True,
                status="ACTIVE",
                effective_from=datetime.now(timezone.utc),
            )
        )
    session.commit()
