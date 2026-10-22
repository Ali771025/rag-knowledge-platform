"""Centralized Celery beat schedule definitions.

The schedule is intentionally task-name based so beat does not need to import
task modules eagerly. This keeps startup/import behavior predictable.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any


def get_celery_beat_schedule() -> dict[str, dict[str, Any]]:
    """Return Celery-native periodic schedule entries."""
    return {
        "memory.cleanup_expired_sessions.5m": {
            "task": "app.tasks.memory.cleanup_expired_sessions",
            "schedule": timedelta(minutes=5),
        },
        "analytics.aggregate_daily_metrics.1h": {
            "task": "app.tasks.analytics.aggregate_daily_metrics",
            "schedule": timedelta(hours=1),
        },
        "analytics.calculate_cost_reports.24h": {
            "task": "app.tasks.analytics.calculate_cost_reports",
            "schedule": timedelta(hours=24),
        },
        "analytics.generate_usage_insights.24h": {
            "task": "app.tasks.analytics.generate_usage_insights",
            "schedule": timedelta(hours=24),
        },
        "knowledge.rebuild_incremental_graph.7d": {
            "task": "app.tasks.knowledge.rebuild_knowledge_graph",
            "schedule": timedelta(days=7),
            "kwargs": {"scope": "incremental"},
        },
        "token_usage.generate_optimization_recommendations.6h": {
            "task": "app.tasks.token_usage.generate_optimization_recommendations",
            "schedule": timedelta(hours=6),
        },
    }


__all__ = ["get_celery_beat_schedule"]
