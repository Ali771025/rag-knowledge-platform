from __future__ import annotations

import base64
import logging
from io import BytesIO
from pathlib import Path
from uuid import UUID
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Request, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.conversation_memory.exceptions import (
    ContextBuildError,
    DialogueManagerError,
    InvalidSessionStateError,
    MemoryPolicyError,
    RedisRepositoryError,
    SessionNotFoundError,
)
from app.conversation_memory.models import ConversationState
from app.conversation_memory.service import ConversationMemoryService
from app.schemas.conversation import ChatAttachment, ChatRequest, ChatResponse, ErrorResponse

router = APIRouter()
logger = logging.getLogger(__name__)
_MAX_CHAT_ATTACHMENT_BYTES = min(int(getattr(settings, "admin_knowledge_upload_max_bytes", 25 * 1024 * 1024)), 8 * 1024 * 1024)
_MAX_CHAT_ATTACHMENT_TEXT_CHARS = 12_000
_SUPPORTED_DOCUMENT_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".doc", ".docx"}


def _error_response(
    status_code: int,
    error: str,
    code: str,
    detail: str | None = None,
) -> JSONResponse:
    payload = ErrorResponse(error=error, code=code, detail=detail).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=payload)


def _parse_uuid_optional(raw: object) -> UUID | None:
    text = str(raw or "").strip()
    if not text:
        return None
    return UUID(text)


def _normalize_form_labels(values: list[object]) -> list[str] | None:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        label = " ".join(str(raw or "").strip().split()).lower()
        if not label or label in seen:
            continue
        seen.add(label)
        normalized.append(label)
    return normalized or None


def _trim_text(value: str | None) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    return text[:_MAX_CHAT_ATTACHMENT_TEXT_CHARS]


def _extract_docx_text(content: bytes) -> str | None:
    try:
        import zipfile

        with zipfile.ZipFile(BytesIO(content)) as archive:
            xml_bytes = archive.read("word/document.xml")
    except Exception:
        return None

    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return None

    chunks: list[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            chunks.append(node.text)
    return _trim_text(" ".join(chunks))


def _extract_pdf_text(content: bytes) -> str | None:
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            reader = module.PdfReader(BytesIO(content))
            texts: list[str] = []
            for page in getattr(reader, "pages", [])[:10]:
                extracted = page.extract_text() if hasattr(page, "extract_text") else ""
                if extracted:
                    texts.append(extracted)
            return _trim_text("\n".join(texts))
        except Exception:
            continue
    return None


def _extract_attachment_text(*, filename: str, content_type: str, content: bytes) -> str | None:
    extension = Path(filename).suffix.lower()
    if content_type.startswith("text/") or extension in {".txt", ".md", ".markdown"}:
        try:
            return _trim_text(content.decode("utf-8"))
        except UnicodeDecodeError:
            return _trim_text(content.decode("latin-1", errors="ignore"))

    if extension == ".docx":
        return _extract_docx_text(content)

    if extension == ".pdf":
        return _extract_pdf_text(content)

    if content_type.startswith("image/"):
        encoded = base64.b64encode(content).decode("ascii")
        snippet = encoded[:8_000]
        return _trim_text(
            f"Image attachment {filename} ({content_type}, {len(content)} bytes). Base64 snippet: {snippet}"
        )

    return None


async def _parse_chat_request(request: Request) -> tuple[ChatRequest | None, JSONResponse | None]:
    content_type = request.headers.get("content-type", "").lower()
    if "multipart/form-data" not in content_type:
        try:
            payload = ChatRequest.model_validate(await request.json())
            return payload, None
        except Exception as exc:
            return None, _error_response(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error="Invalid chat request payload.",
                code="invalid_chat_payload",
                detail=str(exc),
            )

    form = await request.form()
    files = [item for item in form.getlist("files") if isinstance(item, UploadFile)]
    raw_message = str(form.get("message", "") or "").strip()
    message = raw_message or ("Please review the attached files." if files else "")
    if not message:
        return None, _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="Message cannot be empty.",
            code="invalid_message",
        )

    attachments: list[ChatAttachment] = []
    for upload in files:
        file_name = (upload.filename or "attachment").strip() or "attachment"
        content_type_value = str(upload.content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
        extension = Path(file_name).suffix.lower()
        if not (content_type_value.startswith("image/") or content_type_value.startswith("text/") or extension in _SUPPORTED_DOCUMENT_EXTENSIONS):
            continue

        data = await upload.read()
        if len(data) > _MAX_CHAT_ATTACHMENT_BYTES:
            return None, _error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                error=f"Attachment '{file_name}' exceeds max allowed size.",
                code="attachment_too_large",
            )

        if content_type_value.startswith("image/"):
            kind = "image"
        elif content_type_value.startswith("text/"):
            kind = "text"
        elif extension in _SUPPORTED_DOCUMENT_EXTENSIONS:
            kind = "document"
        else:
            kind = "binary"

        attachments.append(
            ChatAttachment(
                filename=file_name,
                content_type=content_type_value,
                kind=kind,
                extracted_text=_extract_attachment_text(
                    filename=file_name,
                    content_type=content_type_value,
                    content=data,
                ),
                size_bytes=len(data),
            )
        )

    labels = _normalize_form_labels(form.getlist("knowledge_labels"))
    memory_scope_raw = str(form.get("memory_scope", "") or "").strip()
    referral_invite_code_raw = str(form.get("referral_invite_code", "") or "").strip()

    try:
        payload = ChatRequest(
            session_id=_parse_uuid_optional(form.get("session_id")),
            user_id=_parse_uuid_optional(form.get("user_id")),
            message=message,
            knowledge_labels=labels,
            memory_scope=memory_scope_raw or None,
            referral_invite_code=referral_invite_code_raw or None,
            attachments=attachments or None,
        )
        return payload, None
    except Exception as exc:
        return None, _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="Invalid chat multipart payload.",
            code="invalid_chat_payload",
            detail=str(exc),
        )


@router.post(
    "",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def chat(request: Request) -> ChatResponse | JSONResponse:
    """Thin chat endpoint that delegates workflow to ConversationMemoryService."""
    payload, parse_error = await _parse_chat_request(request)
    if parse_error is not None or payload is None:
        return parse_error or _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="Invalid chat payload.",
            code="invalid_chat_payload",
        )

    service = ConversationMemoryService()
    try:
        result = await service.handle_user_message(
            session_id=str(payload.session_id) if payload.session_id else None,
            user_id=str(payload.user_id) if payload.user_id else None,
            message=payload.message,
            knowledge_labels=payload.knowledge_labels,
            memory_scope=payload.memory_scope,
            referral_invite_code=payload.referral_invite_code,
            attachments=[item.model_dump(mode="python") for item in (payload.attachments or [])],
        )

        if not result.success:
            error_code = (result.error_code or "conversation_error").lower()
            if error_code == "invalid_message":
                return _error_response(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error=result.message,
                    code=result.error_code or "invalid_message",
                )
            return _error_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error=result.message,
                code=result.error_code or "conversation_unavailable",
                detail="Service could not complete the request.",
            )

        response_session_id = UUID(str(result.data.get("session_id"))) if result.data.get("session_id") else payload.session_id
        if response_session_id is None:
            return _error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error="Missing session identifier in service response.",
                code="missing_session_id",
            )

        response_state = result.state or ConversationState.START
        return ChatResponse(
            session_id=response_session_id,
            message=result.message,
            state=response_state,
            actions=result.actions,
        )
    except SessionNotFoundError as exc:
        logger.warning("chat.session_not_found session_id=%s", payload.session_id)
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error="Session not found.",
            code="session_not_found",
            detail=str(exc),
        )
    except InvalidSessionStateError as exc:
        logger.warning("chat.invalid_session_state session_id=%s", payload.session_id)
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="Invalid session state.",
            code="invalid_session_state",
            detail=str(exc),
        )
    except (RedisRepositoryError, MemoryPolicyError) as exc:
        logger.warning("chat.backend_unavailable error=%s", type(exc).__name__)
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error="Conversation backend unavailable.",
            code="memory_backend_unavailable",
            detail=str(exc),
        )
    except (ContextBuildError, DialogueManagerError) as exc:
        logger.warning("chat.processing_failed error=%s", type(exc).__name__)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="Conversation processing failed.",
            code="conversation_processing_failed",
            detail=str(exc),
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("chat.unhandled_exception")
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="Unexpected conversation error.",
            code="conversation_unexpected_error",
            detail=str(exc),
        )
