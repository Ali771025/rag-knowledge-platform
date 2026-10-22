"""Semantic chunking processor."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid5

from app.ingestion.exceptions import ProcessorError
from app.ingestion.schemas import CleanedDocument, DocumentChunk

logger = logging.getLogger(__name__)

TARGET_TOKENS = 300
MIN_TOKENS = 200
MAX_TOKENS = 400
OVERLAP_TOKENS = 50


@dataclass(slots=True)
class _ChunkPiece:
    """Internal semantic piece before chunk assembly."""

    text: str
    is_heading: bool


class SemanticChunkerProcessor:
    """Builds semantic chunks with deterministic IDs and controlled overlap."""

    def chunk_document(self, document: CleanedDocument, metadata: dict | None = None) -> list[DocumentChunk]:
        """Chunk a cleaned document into semantic chunks."""
        try:
            base_metadata: dict[str, Any] = dict(metadata or {})
            pieces = self._split_semantic_pieces(document.cleaned_text)
            if not pieces:
                return []

            chunk_texts = self._assemble_chunks(pieces)
            chunk_texts = self._apply_overlap(chunk_texts)

            chunks: list[DocumentChunk] = []
            for index, chunk_text_value in enumerate(chunk_texts):
                chunk_text_value = chunk_text_value.strip()
                if not chunk_text_value:
                    continue
                token_count = self._token_count(chunk_text_value)
                content_hash = hashlib.sha256(chunk_text_value.encode("utf-8", errors="ignore")).hexdigest()
                chunk_id = self._deterministic_chunk_id(document.document_id, index, content_hash)
                metadata_json = {
                    **base_metadata,
                    "position_index": index,
                    "token_count": token_count,
                    "target_tokens": TARGET_TOKENS,
                    "min_tokens": MIN_TOKENS,
                    "max_tokens": MAX_TOKENS,
                    "overlap_tokens": OVERLAP_TOKENS,
                }
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document.document_id,
                        chunk_index=index,
                        text=chunk_text_value,
                        token_count=token_count,
                        content_hash=content_hash,
                        metadata_json=metadata_json,
                    )
                )
            logger.info(
                "chunk_document_completed",
                extra={"document_id": str(document.document_id), "chunk_count": len(chunks)},
            )
            return chunks
        except Exception as exc:
            logger.exception("chunk_document_failed", exc_info=exc)
            if isinstance(exc, ProcessorError):
                raise
            raise ProcessorError("failed to chunk document") from exc

    def chunk_batch(self, documents: list[CleanedDocument]) -> list[DocumentChunk]:
        """Chunk multiple documents and flatten output."""
        output: list[DocumentChunk] = []
        for document in documents:
            output.extend(self.chunk_document(document))
        return output

    def _split_semantic_pieces(self, text: str) -> list[_ChunkPiece]:
        sections = re.split(r"\n\s*\n+", text.strip())
        pieces: list[_ChunkPiece] = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            lines = [line.strip() for line in section.splitlines() if line.strip()]
            if not lines:
                continue
            if self._is_heading(lines[0]):
                pieces.append(_ChunkPiece(text=lines[0], is_heading=True))
                remainder = "\n".join(lines[1:]).strip()
                if remainder:
                    pieces.append(_ChunkPiece(text=remainder, is_heading=False))
            else:
                pieces.append(_ChunkPiece(text="\n".join(lines), is_heading=False))
        return pieces

    def _assemble_chunks(self, pieces: list[_ChunkPiece]) -> list[str]:
        chunks: list[str] = []
        current_parts: list[str] = []
        current_tokens = 0

        for piece in pieces:
            piece_tokens = self._token_count(piece.text)
            if piece_tokens == 0:
                continue

            # If an individual piece is too large, flush current and split piece token-wise.
            if piece_tokens > MAX_TOKENS:
                split_pieces = self._token_split(piece.text)
                if current_parts:
                    prefix = "\n\n".join(current_parts).strip()
                    if split_pieces and current_tokens < MIN_TOKENS:
                        split_pieces[0] = f"{prefix}\n\n{split_pieces[0]}".strip()
                    else:
                        chunks.append(prefix)
                    current_parts = []
                    current_tokens = 0
                chunks.extend(split_pieces)
                continue

            projected = current_tokens + piece_tokens
            if projected <= MAX_TOKENS:
                current_parts.append(piece.text)
                current_tokens = projected
                continue

            # Would exceed max. If current chunk has enough content, flush and start next.
            if current_tokens >= MIN_TOKENS:
                chunks.append("\n\n".join(current_parts).strip())
                current_parts = [piece.text]
                current_tokens = piece_tokens
            else:
                # Current chunk is underfilled; force include to preserve boundary, then flush.
                current_parts.append(piece.text)
                current_tokens = projected
                chunks.append("\n\n".join(current_parts).strip())
                current_parts = []
                current_tokens = 0

        if current_parts:
            chunks.append("\n\n".join(current_parts).strip())

        # Merge tiny tail chunk if possible.
        if len(chunks) >= 2:
            last_tokens = self._token_count(chunks[-1])
            prev_tokens = self._token_count(chunks[-2])
            if last_tokens < MIN_TOKENS and (last_tokens + prev_tokens) <= MAX_TOKENS + OVERLAP_TOKENS:
                chunks[-2] = f"{chunks[-2]}\n\n{chunks[-1]}".strip()
                chunks.pop()

        return [chunk for chunk in chunks if chunk.strip()]

    def _token_split(self, text: str) -> list[str]:
        matches = list(re.finditer(r"\b[\w'-]+\b", text, flags=re.UNICODE))
        if not matches:
            return []
        chunks: list[str] = []
        start = 0
        while start < len(matches):
            end = min(start + TARGET_TOKENS, len(matches))
            if (end - start) < MIN_TOKENS and chunks:
                # Merge short tail into previous chunk.
                tail = text[matches[start].start() : matches[end - 1].end()].strip()
                chunks[-1] = f"{chunks[-1]}\n\n{tail}".strip()
                break
            chunks.append(text[matches[start].start() : matches[end - 1].end()].strip())
            if end >= len(matches):
                break
            start = end
        return chunks

    def _apply_overlap(self, chunk_texts: list[str]) -> list[str]:
        if not chunk_texts:
            return []
        output: list[str] = []
        previous_tokens: list[str] = []
        for index, text in enumerate(chunk_texts):
            current_tokens = self._tokenize(text)
            if index == 0:
                output.append(text.strip())
                previous_tokens = current_tokens
                continue

            overlap_tokens = previous_tokens[-OVERLAP_TOKENS:] if previous_tokens else []
            prefix = " ".join(overlap_tokens).strip()
            output.append(f"{prefix}\n\n{text.strip()}".strip() if prefix else text.strip())
            previous_tokens = current_tokens
        return output

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\b[\w'-]+\b", text)

    def _token_count(self, text: str) -> int:
        return len(self._tokenize(text))

    def _is_heading(self, line: str) -> bool:
        stripped = line.strip()
        if re.match(r"^#{1,6}\s+.+", stripped):
            return True
        if len(stripped) <= 120 and stripped.isupper():
            return True
        if stripped.endswith(":") and len(stripped.split()) <= 10:
            return True
        return False

    def _deterministic_chunk_id(self, document_id: UUID, position_index: int, content_hash: str) -> UUID:
        key = f"{document_id}:{position_index}:{content_hash}"
        return uuid5(document_id, key)


def chunk_text(content: str, chunk_size: int = 500) -> list[str]:
    """Backward-compatible helper used by earlier skeletons."""
    if chunk_size <= 0:
        return [content]
    words = re.findall(r"\b[\w'-]+\b", content)
    if not words:
        return [""]
    windows: list[str] = []
    for start in range(0, len(words), chunk_size):
        windows.append(" ".join(words[start : start + chunk_size]))
    return windows
