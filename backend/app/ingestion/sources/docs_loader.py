"""Documentation directory loader implementation."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from app.ingestion.exceptions import IngestionValidationError
from app.ingestion.schemas import RawDocument, SourceConfig
from app.ingestion.sources.base import BaseSourceLoader

logger = logging.getLogger(__name__)

SUPPORTED_DOC_EXTENSIONS = {".md", ".markdown", ".txt"}


class DocsLoaderSource(BaseSourceLoader):
    """Recursively loads documentation files from directories."""

    async def load(self, config: SourceConfig) -> list[RawDocument]:
        """Load markdown/txt files from a docs directory into RawDocument records."""
        self.validate_source(config)
        if config.source_type != "docs":
            raise IngestionValidationError("DocsLoaderSource requires source_type='docs'")

        root = Path(config.source_uri).expanduser()
        if not root.exists() or not root.is_dir():
            raise IngestionValidationError(f"Documentation directory does not exist: {root}")

        file_paths = await asyncio.to_thread(self._collect_supported_files, root)
        documents: list[RawDocument] = []
        for file_path in file_paths:
            if len(documents) >= config.max_items:
                break
            parsed = await asyncio.to_thread(self._read_doc_file, file_path)
            if parsed is None:
                continue
            text = parsed["text"].strip()
            if not text:
                continue

            relative_path = file_path.relative_to(root).as_posix()
            path_parts = Path(relative_path).parts
            hierarchy = list(path_parts[:-1])

            per_file_config = config.model_copy(update={"source_uri": relative_path})
            document = self.build_raw_document(
                config=per_file_config,
                raw_content=text,
                title=parsed.get("title") or file_path.stem,
                metadata={
                    "headings": parsed.get("headings", []),
                    "heading_hierarchy": parsed.get("heading_hierarchy", []),
                    "relative_path": relative_path,
                    "document_hierarchy": hierarchy,
                    "file_name": file_path.name,
                    "file_type": file_path.suffix.lower(),
                    "file_size": file_path.stat().st_size,
                    "metadata": parsed.get("metadata", {}),
                },
            )
            documents.append(document)

        logger.info(
            "docs_loader_completed",
            extra={"root_path": str(root), "files_discovered": len(file_paths), "documents_collected": len(documents)},
        )
        return documents

    def _collect_supported_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in SUPPORTED_DOC_EXTENSIONS:
                files.append(path)
        files.sort(key=lambda item: str(item).lower())
        return files

    def _read_doc_file(self, file_path: Path) -> dict[str, Any] | None:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("docs_loader_read_failed", extra={"path": str(file_path), "error": str(exc)})
            return None

        headings, hierarchy = self._extract_headings_with_hierarchy(text)
        title = headings[0] if headings else file_path.stem
        return {
            "text": text,
            "headings": headings,
            "heading_hierarchy": hierarchy,
            "metadata": {},
            "title": title,
        }

    def _extract_headings_with_hierarchy(self, text: str) -> tuple[list[str], list[dict[str, Any]]]:
        headings: list[str] = []
        hierarchy: list[dict[str, Any]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            markdown_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if markdown_match:
                level = len(markdown_match.group(1))
                title = markdown_match.group(2).strip()
                headings.append(title)
                hierarchy.append({"level": level, "title": title})
                continue
            if stripped.isupper() and len(stripped) <= 100:
                title = stripped.title()
                headings.append(title)
                hierarchy.append({"level": 2, "title": title})
        return headings, hierarchy
