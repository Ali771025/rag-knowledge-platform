from __future__ import annotations

import time

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.redis_client import get_redis_client

_START_TIME = time.monotonic()
router = APIRouter()


def check_redis() -> str:
    try:
        return "ok" if bool(get_redis_client().ping()) else "down"
    except Exception:
        return "down"


def check_db() -> str:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "down"
    finally:
        db.close()


def get_system_uptime() -> float:
    return round(time.monotonic() - _START_TIME, 2)


def health_check() -> dict[str, object]:
    return {
        "status": "ok",
        "redis": check_redis(),
        "database": check_db(),
        "uptime": get_system_uptime(),
    }


@router.get("/health")
def get_health() -> dict[str, object]:
    return health_check()
