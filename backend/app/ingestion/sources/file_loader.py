"""File source loader implementation."""

from __future__ import annotations

import asyncio
import logging
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from app.ingestion.exceptions import IngestionValidationError, SourceLoadError
from app.ingestion.schemas import RawDocument, SourceConfig
from app.ingestion.sources.base import BaseSourceLoader

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".markdown", ".txt"}


class FileLoaderSource(BaseSourceLoader):
    """Loads single-file content into normalized raw documents."""

    async def load(self, config: SourceConfig) -> list[RawDocument]:
        """Load one file and return one RawDocument (or empty when unreadable)."""
        self.validate_source(config)
        if config.source_type != "file":
            raise IngestionValidationError("FileLoaderSource requires source_type='file'")

        file_path = Path(config.source_uri).expanduser()
        if not file_path.exists() or not file_path.is_file():
            raise IngestionValidationError(f"File does not exist: {file_path}")
        self._validate_extension(file_path)

        parsed = await asyncio.to_thread(self._read_file, file_path)
        if parsed is None:
            raise SourceLoadError(f"Unable to read file content: {file_path.name}")

        text = parsed["text"].strip()
        if not text:
            logger.warning("file_loader_empty_content", extra={"path": str(file_path)})
            raise SourceLoadError(f"Extracted file content is empty: {file_path.name}")

        raw_document = self.build_raw_document(
            config=config,
            raw_content=text,
            title=parsed.get("title") or file_path.name,
            metadata={
                "headings": parsed.get("headings", []),
                "file_name": file_path.name,
                "file_type": file_path.suffix.lower(),
                "file_size": file_path.stat().st_size,
                "metadata": parsed.get("metadata", {}),
            },
        )
        return [raw_document]

    def _validate_extension(self, file_path: Path) -> None:
        extension = file_path.suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise IngestionValidationError(
                f"Unsupported file type '{extension}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
            )

    def _read_file(self, file_path: Path) -> dict[str, Any] | None:
        extension = file_path.suffix.lower()
        try:
            if extension == ".pdf":
                return self._read_pdf(file_path)
            if extension == ".docx":
                return self._read_docx(file_path)
            if extension in {".md", ".markdown"}:
                return self._read_markdown(file_path)
            if extension == ".txt":
                return self._read_text(file_path)
        except Exception as exc:
            logger.warning("file_loader_read_failed", extra={"path": str(file_path), "error": str(exc)})
            return None
        return None

    def _read_pdf(self, file_path: Path) -> dict[str, Any]:
        try:
            from PyPDF2 import PdfReader
        except Exception as exc:  # pragma: no cover - dependency optional
            raise SourceLoadError("PyPDF2 is required for PDF loading") from exc
        reader = PdfReader(str(file_path))
        text_parts: list[str] = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        text = "\n".join(text_parts).strip()
        metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
        headings = self._extract_markdown_like_headings(text)
        return {"text": text, "headings": headings, "metadata": metadata, "title": metadata.get("/Title")}

    def _read_docx(self, file_path: Path) -> dict[str, Any]:
        try:
            from docx import Document as DocxDocument
            return self._read_docx_with_python_docx(file_path=file_path, docx_document_cls=DocxDocument)
        except Exception:  # pragma: no cover - dependency optional
            logger.info(
                "file_loader_docx_dependency_missing_fallback_xml",
                extra={"path": str(file_path)},
            )
            return self._read_docx_without_dependency(file_path)

    def _read_docx_with_python_docx(self, *, file_path: Path, docx_document_cls) -> dict[str, Any]:
        doc = docx_document_cls(str(file_path))
        paragraphs = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
        table_lines: list[str] = []
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        value = paragraph.text.strip()
                        if value:
                            table_lines.append(value)

        # Preserve document order while deduplicating repetitive table cells.
        seen_lines: set[str] = set()
        merged_lines: list[str] = []
        for line in [*paragraphs, *table_lines]:
            key = line.casefold()
            if key in seen_lines:
                continue
            seen_lines.add(key)
            merged_lines.append(line)

        text = "\n".join(merged_lines).strip()
        headings = [
            paragraph.text.strip()
            for paragraph in doc.paragraphs
            if paragraph.text.strip() and paragraph.style and "heading" in paragraph.style.name.lower()
        ]
        metadata: dict[str, Any] = {}
        core = doc.core_properties
        if core.author:
            metadata["author"] = core.author
        if core.title:
            metadata["title"] = core.title
        if core.created:
            metadata["created"] = str(core.created)
        return {"text": text, "headings": headings, "metadata": metadata, "title": metadata.get("title")}

    def _read_docx_without_dependency(self, file_path: Path) -> dict[str, Any]:
        try:
            with zipfile.ZipFile(file_path, "r") as archive:
                xml_bytes = archive.read("word/document.xml")
        except Exception as exc:
            raise SourceLoadError("unable to read DOCX XML content") from exc

        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as exc:
            raise SourceLoadError("unable to parse DOCX XML content") from exc

        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", namespace):
            text_nodes = paragraph.findall(".//w:t", namespace)
            paragraph_text = "".join(node.text or "" for node in text_nodes).strip()
            if paragraph_text:
                paragraphs.append(paragraph_text)

        text = "\n".join(paragraphs).strip()
        headings = self._extract_markdown_like_headings(text)
        return {"text": text, "headings": headings, "metadata": {}, "title": None}

    def _read_markdown(self, file_path: Path) -> dict[str, Any]:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        headings = self._extract_markdown_headings(text)
        title = headings[0] if headings else file_path.stem
        return {"text": text, "headings": headings, "metadata": {}, "title": title}

    def _read_text(self, file_path: Path) -> dict[str, Any]:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        headings = self._extract_markdown_like_headings(text)
        title = headings[0] if headings else file_path.stem
        return {"text": text, "headings": headings, "metadata": {}, "title": title}

    def _extract_markdown_headings(self, text: str) -> list[str]:
        headings: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if re.match(r"^#{1,6}\s+.+", line):
                headings.append(re.sub(r"^#{1,6}\s+", "", line).strip())
        return headings

    def _extract_markdown_like_headings(self, text: str) -> list[str]:
        """Best-effort heading extraction when formal markdown is unknown."""
        headings = self._extract_markdown_headings(text)
        if headings:
            return headings
        candidates: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if 0 < len(stripped) <= 80 and stripped.isupper():
                candidates.append(stripped.title())
        return candidates
