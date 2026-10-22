from __future__ import annotations

import logging
import hashlib
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.internal.policy.loader import load_default_policy_config
from app.middleware.observability_middleware import ObservabilityMiddleware
from app.middleware.rate_limiter import enforce_rate_limit
from app.middleware.rfp_guard import enforce_rfp_guard
from app.middleware.request_validator import validate_request_middleware
from app.qora.api.internal_state import router as qora_internal_router
from app.qora.api.readiness import router as qora_readiness_router

configure_logging(str(getattr(settings, "log_level", "INFO")))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app
    logger.info("Application startup")
    load_default_policy_config()
    yield
    logger.info("Application shutdown")


app = FastAPI(
    title=str(getattr(settings, "app_name", "RAGAi Backend")),
    version=str(getattr(settings, "app_version", "0.1.0")),
    debug=bool(getattr(settings, "debug", False)),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.invalid", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ObservabilityMiddleware)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_host = request.client.host if request.client else "anonymous"
    authorization = request.headers.get("authorization", "")
    # Never trust a caller-controlled x-user-id header. A token digest gives a stable,
    # non-sensitive rate-limit key before authentication middleware runs.
    effective_user_id = (
        hashlib.sha256(authorization.encode("utf-8")).hexdigest()
        if authorization.lower().startswith("bearer ")
        else client_host
    )
    path = request.url.path
    limit_override: int | None = None
    if path.startswith("/api/v1/admin/token-usage/realtime"):
        limit_override = max(int(getattr(settings, "rate_limit", 100)) * 2, 200)
    try:
        enforce_rate_limit(effective_user_id, limit_override=limit_override)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})
    return await call_next(request)


@app.middleware("http")
async def rfp_guard_middleware(request: Request, call_next):
    return await enforce_rfp_guard(request, call_next)


@app.middleware("http")
async def request_validation_middleware(request: Request, call_next):
    return await validate_request_middleware(request, call_next)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(
        "http_exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "detail": str(exc.detail),
        },
    )
    response_body: dict[str, str] = {"detail": str(exc.detail)}
    if exc.status_code in {400, 401, 403, 429}:
        response_body["error_type"] = f"HTTP_{exc.status_code}"
    return JSONResponse(status_code=exc.status_code, content=response_body)


@app.exception_handler(RequestValidationError)  # type: ignore[misc]
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(
        "request_validation_error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": 422,
            "errors": exc.errors(),
        },
    )
    return JSONResponse(status_code=422, content={"detail": "Request validation failed", "errors": exc.errors()})


@app.exception_handler(Exception)  # type: ignore[misc]
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=exc,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/", tags=["meta"])
def root() -> dict[str, Any]:
    return {"service": app.title, "version": app.version}


app.include_router(api_router, prefix=str(getattr(settings, "api_v1_prefix", "/api/v1")))
app.include_router(qora_internal_router)
app.include_router(qora_readiness_router)
