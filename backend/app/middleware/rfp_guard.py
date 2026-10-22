from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

_BLOCKED_ENDPOINT_KEYWORDS = {"transaction", "financial", "blockchain", "wallet", "transfer"}
_MUTATING_METHODS = {"PUT", "PATCH", "DELETE"}
_ALLOWED_WRITE_PREFIXES = {
    "/api/v1/chat",
    "/api/v1/auth",
    "/api/v1/session/start",
    "/api/v1/admin/knowledge",
    "/api/v1/admin/rag",
}
_ALLOWED_MUTATION_PREFIXES = {"/api/v1/admin/knowledge/sources", "/api/v1/admin/rag"}
_ALLOWED_READ_EXACT = {"/api/v1/metrics"}
_ALLOWED_WRITE_EXACT = {
    "/api/v1/admin/ingest/url",
    "/api/v1/admin/ingest/discord",
    "/api/v1/kg/expand",
    "/api/v1/kg/context",
    "/api/v1/rag/query",
    "/api/v1/rag/generate",
    "/api/v1/persona/analyze",
    "/api/v1/conversion/update",
    "/api/v1/users/assessment",
    "/api/v1/users/state/update",
    "/api/v1/users/profile",
    "/api/v1/audio/transcribe",
    "/api/v1/audio/speech",
}


def _is_allowed_mutation(path: str, method: str) -> bool:
    normalized = path.rstrip("/")
    if normalized in _ALLOWED_WRITE_EXACT:
        return True
    if method.upper() == "POST":
        return any(normalized.startswith(prefix) for prefix in _ALLOWED_WRITE_PREFIXES)
    if method.upper() in {"PUT", "PATCH", "DELETE"}:
        return any(normalized.startswith(prefix) for prefix in _ALLOWED_MUTATION_PREFIXES)
    return False


async def enforce_rfp_guard(request: Request, call_next):
    path = request.url.path.lower()
    method = request.method.upper()

    if method == "GET" and path in _ALLOWED_READ_EXACT:
        return await call_next(request)

    if any(keyword in path for keyword in _BLOCKED_ENDPOINT_KEYWORDS):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Blocked by Phase 1 RFP security policy"},
        )

    if method in _MUTATING_METHODS and path.startswith("/api/v1") and not _is_allowed_mutation(path, method):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "External mutation endpoints are disabled in Phase 1"},
        )

    if method == "POST" and path.startswith("/api/v1") and not _is_allowed_mutation(path, method):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Write access is restricted by Phase 1 RFP policy"},
        )

    return await call_next(request)
