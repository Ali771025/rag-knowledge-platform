from __future__ import annotations

from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

TOKEN_MONITORING_TABLES: tuple[str, ...] = (
    "api_keys",
    "token_usage_logs",
    "daily_aggregates",
    "optimization_recommendations",
    "budget_alerts",
    "api_key_budget_configs",
    "budget_change_audit_logs",
)


@lru_cache(maxsize=1)
def _placeholder_table_name() -> str:
    return TOKEN_MONITORING_TABLES[0]


def token_monitoring_tables_ready(db: Session) -> bool:
    dialect = db.bind.dialect.name if db.bind is not None else ""
    if dialect == "sqlite":
        statement = text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name")
    else:
        statement = text("SELECT to_regclass(:name)")

    try:
        for table_name in TOKEN_MONITORING_TABLES:
            value = db.scalar(statement, {"name": table_name})
            if value in (None, ""):
                return False
        return True
    except SQLAlchemyError:
        return False
