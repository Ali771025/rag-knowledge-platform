from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.redis_client import get_redis_client
from app.qora.infrastructure.persistence.models import (
    AchievementDefinition,
    LevelDefinition,
    ProductCatalogItem,
    ProductWeightTableVersion,
    ReferralRuleDefinition,
)


router = APIRouter(tags=["health"])


@router.get("/health")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def readiness(db: Session = Depends(get_db)):
    checks: dict[str, dict[str, str | bool]] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"ready": True, "detail": "reachable"}
        checks["state_store"] = {"ready": True, "detail": "database-backed"}
    except Exception as exc:
        db.rollback()
        checks["database"] = {"ready": False, "detail": type(exc).__name__}
        checks["state_store"] = {"ready": False, "detail": "database unavailable"}

    try:
        cache_ready = bool(get_redis_client().ping())
        checks["cache"] = {"ready": cache_ready, "detail": "reachable" if cache_ready else "unavailable"}
    except Exception as exc:
        checks["cache"] = {"ready": False, "detail": type(exc).__name__}

    llm_ready = bool(settings.openai_api_key or settings.anthropic_api_key)
    checks["llm"] = {"ready": llm_ready, "detail": "configured" if llm_ready else "provider key missing"}
    prompt_version = os.getenv("QORA_PROMPT_VERSION", "").strip()
    checks["active_prompt_version"] = {
        "ready": bool(prompt_version),
        "detail": prompt_version or "QORA_PROMPT_VERSION is missing",
    }

    try:
        now = datetime.now(timezone.utc)
        weight = db.scalar(
            select(ProductWeightTableVersion).where(
                ProductWeightTableVersion.status == "ACTIVE",
                ProductWeightTableVersion.effective_from <= now,
                (
                    ProductWeightTableVersion.effective_to.is_(None)
                    | (ProductWeightTableVersion.effective_to > now)
                ),
            )
        )
        checks["weight_table"] = {"ready": weight is not None, "detail": weight.weight_table_version if weight else "missing"}
        rag_product = db.scalar(
            select(ProductCatalogItem).where(
                ProductCatalogItem.is_active.is_(True),
                ProductCatalogItem.rag_ready.is_(True),
                ProductCatalogItem.compliance_flag == "CLEAR",
            ).limit(1)
        )
        checks["rag"] = {
            "ready": rag_product is not None,
            "detail": "published product scope available" if rag_product else "no compliance-cleared RAG product",
        }
        level = db.scalar(select(LevelDefinition).where(LevelDefinition.status == "ACTIVE").limit(1))
        referral = db.scalar(select(ReferralRuleDefinition).where(ReferralRuleDefinition.status == "ACTIVE").limit(1))
        # Achievement definitions can intentionally be empty; the rule framework must still be active.
        achievement = db.scalar(select(AchievementDefinition).where(AchievementDefinition.status == "ACTIVE").limit(1))
        achievement_ready = level is not None and referral is not None
        checks["achievement_rules"] = {
            "ready": achievement_ready,
            "detail": "active definitions available" if achievement else "framework active; no approved achievement definitions",
        }
    except Exception as exc:
        db.rollback()
        for key in ("weight_table", "rag", "achievement_rules"):
            checks[key] = {"ready": False, "detail": type(exc).__name__}

    ready = all(bool(item["ready"]) for item in checks.values())
    payload = {"status": "ready" if ready else "not_ready", "checks": checks}
    return JSONResponse(status_code=200 if ready else 503, content=payload)
