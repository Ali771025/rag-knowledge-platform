"""Ingestion service orchestration."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.celery_app import CeleryConfigurationError, get_celery_app
from app.core.database import SessionLocal
from app.ingestion.exceptions import IngestionError, IngestionValidationError
from app.ingestion.indexers.metadata_indexer import MetadataIndexer, MetadataIndexerError
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.schemas import IngestionRequest, IngestionResult, IngestionPipelineResult, SourceConfig
from app.models.ingestion_job import IngestionJob
from app.schemas.ingestion import DiscordIngestionRequest, FileIngestionRequest, IngestionResponse, UrlIngestionRequest
from app.tasks.ingestion_tasks import full_ingestion_pipeline_task

logger = logging.getLogger(__name__)


class IngestionService:
    """Thin service layer for ingestion submission and status retrieval."""

    def __init__(
        self,
        pipeline: IngestionPipeline | None = None,
        metadata_indexer: MetadataIndexer | None = None,
    ) -> None:
        self.pipeline = pipeline or IngestionPipeline()
        self.metadata_indexer = metadata_indexer or MetadataIndexer()
        self.default_async_mode = os.getenv("INGESTION_DEFAULT_ASYNC", "true").strip().lower() in {"1", "true", "yes"}

    def submit_url_ingestion(self, request: UrlIngestionRequest) -> IngestionResponse:
        """Submit web URL ingestion request."""
        source_uri = str(request.url)
        config = SourceConfig(
            source_type="web",
            source_uri=source_uri,
            options={
                "title": request.title,
                "tags": list(request.tags),
                **dict(request.metadata_json or {}),
            },
        )
        return self._submit_ingestion(config=config, request_metadata=request.metadata_json or {})

    def submit_discord_ingestion(self, request: DiscordIngestionRequest) -> IngestionResponse:
        """Submit Discord ingestion request."""
        source_uri = f"discord://guild/{request.guild_id}/channel/{request.channel_id}"
        config = SourceConfig(
            source_type="discord",
            source_uri=source_uri,
            max_items=request.message_limit,
            options={
                "guild_id": request.guild_id,
                "channel_id": request.channel_id,
                "message_limit": request.message_limit,
                **dict(request.metadata_json or {}),
            },
        )
        return self._submit_ingestion(config=config, request_metadata=request.metadata_json or {})

    def submit_file_ingestion(self, request: FileIngestionRequest) -> IngestionResponse:
        """Submit file ingestion request."""
        config = SourceConfig(
            source_type="file",
            source_uri=request.file_path,
            options={
                "file_name": request.file_name,
                **dict(request.metadata_json or {}),
            },
        )
        return self._submit_ingestion(config=config, request_metadata=request.metadata_json or {})

    def get_ingestion_status(self, job_id: UUID) -> IngestionResponse:
        """Get ingestion status by job identifier."""
        job = self._get_job(job_id)
        if job is None:
            raise IngestionValidationError(f"ingestion job not found: {job_id}")

        stats_json = dict(job.stats_json or {})
        if self._is_async_proxy_job(job, stats_json):
            self._refresh_async_proxy_status(job, stats_json)
            job = self._get_job(job_id) or job

        return self._to_response(job)

    async def ingest(self, request: IngestionRequest) -> IngestionResult:
        """Backward-compatible async method for older callsites."""
        config = SourceConfig(
            source_type=request.source_type,
            source_uri=request.source_uri,
            max_items=1000,
            timeout_seconds=30,
            options=request.metadata,
        )
        result = self._run_sync_pipeline(config)
        return IngestionResult(
            job_id=result.job_id,
            status=result.status,  # type: ignore[arg-type]
            processed_chunks=result.chunks_total,
            errors=result.errors,
            updated_at=result.updated_at,
        )

    def _submit_ingestion(self, *, config: SourceConfig, request_metadata: dict[str, Any]) -> IngestionResponse:
        run_async = self._resolve_async_mode(request_metadata)
        logger.info(
            "ingestion_submission_received",
            extra={"source_type": config.source_type, "source_uri": config.source_uri, "async_mode": run_async},
        )

        if run_async:
            queued_response = self._queue_async_ingestion(config)
            if queued_response is not None:
                return queued_response

        result = self._run_sync_pipeline(config)
        return IngestionResponse(
            job_id=result.job_id,
            status=result.status,  # type: ignore[arg-type]
            source_type=config.source_type,
            source_uri=config.source_uri,
            message="ingestion completed synchronously",
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    def _run_sync_pipeline(self, config: SourceConfig) -> IngestionPipelineResult:
        try:
            if config.source_type == "web":
                return self.pipeline.ingest_url(config)
            if config.source_type == "discord":
                return self.pipeline.ingest_discord(config)
            if config.source_type == "file":
                return self.pipeline.ingest_file(config)
            raise IngestionValidationError(f"unsupported source type: {config.source_type}")
        except IngestionError:
            raise
        except Exception as exc:
            logger.exception(
                "ingestion_sync_execution_failed",
                extra={"source_type": config.source_type, "source_uri": config.source_uri},
                exc_info=exc,
            )
            raise IngestionError("ingestion pipeline failed") from exc

    def _queue_async_ingestion(self, config: SourceConfig) -> IngestionResponse | None:
        if not hasattr(full_ingestion_pipeline_task, "delay"):
            logger.info("celery_task_delay_unavailable_fallback_sync")
            return None

        if not self._has_active_celery_workers():
            logger.warning(
                "celery_worker_unavailable_fallback_sync",
                extra={"source_type": config.source_type, "source_uri": config.source_uri},
            )
            return None

        try:
            async_result = full_ingestion_pipeline_task.delay(config.source_type, config.model_dump(mode="python"))
            task_id = str(getattr(async_result, "id", "") or "").strip()
            if not task_id:
                logger.warning("celery_task_submission_missing_task_id")
                return None

            proxy_job = self.metadata_indexer.create_ingestion_job(
                source_type=config.source_type,
                source_uri=config.source_uri,
                status="pending",
                stats_json={
                    "mode": "async_proxy",
                    "celery_task_id": task_id,
                },
            )
            logger.info(
                "ingestion_async_task_queued",
                extra={
                    "proxy_job_id": str(proxy_job.id),
                    "celery_task_id": task_id,
                    "source_type": config.source_type,
                },
            )
            return IngestionResponse(
                job_id=proxy_job.id,
                status="pending",
                source_type=config.source_type,
                source_uri=config.source_uri,
                message=f"ingestion queued (task_id={task_id})",
                created_at=proxy_job.created_at,
                updated_at=proxy_job.updated_at,
            )
        except Exception as exc:
            logger.warning(
                "ingestion_async_submission_failed_fallback_sync",
                extra={"source_type": config.source_type, "source_uri": config.source_uri, "error": str(exc)},
            )
            return None

    def _has_active_celery_workers(self) -> bool:
        try:
            app = get_celery_app()
            inspect = app.control.inspect(timeout=1.0)
            if inspect is None:
                return False
            ping_result = inspect.ping()
            return isinstance(ping_result, dict) and bool(ping_result)
        except Exception as exc:
            logger.warning("celery_worker_health_check_failed", extra={"error": str(exc)})
            return False

    def _refresh_async_proxy_status(self, job: IngestionJob, stats_json: dict[str, Any]) -> None:
        task_id = str(stats_json.get("celery_task_id", "")).strip()
        if not task_id:
            return
        try:
            app = get_celery_app()
            async_result = app.AsyncResult(task_id)
            state = str(async_result.state or "").upper()
            if state in {"PENDING", "RECEIVED"}:
                self.metadata_indexer.update_ingestion_job(job.id, status="pending")
                return
            if state in {"STARTED", "RETRY"}:
                self.metadata_indexer.update_ingestion_job(job.id, status="running")
                return
            if state == "SUCCESS":
                payload = async_result.result if isinstance(async_result.result, dict) else {}
                final_status = str(payload.get("status", "completed")).lower()
                safe_status = final_status if final_status in {"pending", "running", "completed", "failed", "partial"} else "completed"
                merged_stats = dict(stats_json)
                merged_stats["pipeline_result"] = payload
                self.metadata_indexer.update_ingestion_job(
                    job.id,
                    status=safe_status,
                    stats_json=merged_stats,
                    completed_at=datetime.now(timezone.utc),
                )
                return
            if state in {"FAILURE", "REVOKED"}:
                error_text = str(async_result.result)
                self.metadata_indexer.update_ingestion_job(
                    job.id,
                    status="failed",
                    error_message=error_text[:2000],
                    completed_at=datetime.now(timezone.utc),
                )
                return
            logger.info("ingestion_async_proxy_unknown_state", extra={"job_id": str(job.id), "state": state})
        except (CeleryConfigurationError, MetadataIndexerError) as exc:
            logger.warning("ingestion_async_proxy_refresh_failed", extra={"job_id": str(job.id), "error": str(exc)})
        except Exception as exc:
            logger.exception("ingestion_async_proxy_refresh_unexpected_error", exc_info=exc)

    def _resolve_async_mode(self, metadata_json: dict[str, Any]) -> bool:
        value = metadata_json.get("async_mode", metadata_json.get("async", self.default_async_mode))
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes"}
        if isinstance(value, (int, float)):
            return bool(value)
        return self.default_async_mode

    def _is_async_proxy_job(self, job: IngestionJob, stats_json: dict[str, Any]) -> bool:
        return str(stats_json.get("mode", "")).strip().lower() == "async_proxy" and job.status in {"pending", "running"}

    def _get_job(self, job_id: UUID) -> IngestionJob | None:
        try:
            with SessionLocal() as session:
                stmt = select(IngestionJob).where(IngestionJob.id == job_id)
                return session.scalar(stmt)
        except Exception as exc:
            logger.exception("ingestion_status_lookup_failed", exc_info=exc)
            raise IngestionError("failed to fetch ingestion status") from exc

    def _to_response(self, job: IngestionJob) -> IngestionResponse:
        return IngestionResponse(
            job_id=job.id,
            status=job.status,  # type: ignore[arg-type]
            source_type=job.source_type,  # type: ignore[arg-type]
            source_uri=job.source_uri,
            message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
