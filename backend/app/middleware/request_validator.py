from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse


def _allows_non_json_post(path: str) -> bool:
    normalized = path.rstrip("/")
    return normalized in {"/api/v1/admin/knowledge/upload", "/api/v1/chat"}


def _requires_bearer_auth(path: str, method: str) -> bool:
    normalized = path.rstrip("/")
    if normalized == "":
        return False
    if normalized == "/api/v1/health":
        return False
    if normalized == "/api/v1/metrics":
        return False
    if normalized == "/api/v1/chat":
        return False
    if normalized.startswith("/api/v1/rag"):
        return False
    if normalized.startswith("/api/v1/admin"):
        return False
    if normalized.startswith("/api/v1/kg"):
        return False
    if method.upper() == "POST" and normalized in {
        "/api/v1/auth/login",
        "/api/v1/auth/admin/login",
        "/api/v1/auth/telegram/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    }:
        return False
    return normalized.startswith("/api/v1")


async def validate_request_middleware(request: Request, call_next):
    method = request.method.upper()

    if method == "POST":
        content_type = request.headers.get("content-type", "")
        content_length = request.headers.get("content-length")
        transfer_encoding = request.headers.get("transfer-encoding", "")
        has_body = False
        if content_length is not None:
            try:
                has_body = int(content_length) > 0
            except ValueError:
                has_body = True
        elif transfer_encoding:
            has_body = True

        if has_body and "application/json" not in content_type and not _allows_non_json_post(request.url.path):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "POST requests must use Content-Type: application/json"},
            )

    if _requires_bearer_auth(request.url.path, method):
        authorization = request.headers.get("authorization")
        if not authorization:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing Authorization header"},
            )
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Malformed Authorization header"},
            )
        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Malformed bearer token"},
            )

    return await call_next(request)
