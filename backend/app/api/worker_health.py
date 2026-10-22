"""Worker health API endpoint for Celery operational visibility."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from app.core.security import require_role
from app.models.user import User
from app.services.tasks.worker_monitor import WorkerMonitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workers", tags=["workers"])


@router.get("/health")
def get_worker_health(admin_user: User = Depends(require_role("admin"))) -> dict[str, Any]:
    """Return Celery worker and queue health summary."""
    logger.info("worker_health_requested", extra={"admin_user_id": str(admin_user.id)})
    monitor = WorkerMonitor()
    return monitor.get_health()

