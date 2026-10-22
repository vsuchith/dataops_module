"""Document parsers for TXT, Markdown, and HTML (E4)."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from src.llmops.compatibility.handoff import CanonicalElement
from src.llmops.compatibility.specs import DocumentFormat, DocumentSourceSpec


class _StrictHTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._stack: list[str] = []
        self._fatal_error: str | None = None

    def error(self, message: str) -> None:
        self._fatal_error = message

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if not self._stack:
            self._fatal_error = f"unexpected closing tag </{normalized}>"
            return
        if self._stack[-1] != normalized:
            self._fatal_error = (
                f"mismatched tag: expected </{self._stack[-1]}>, got </{normalized}>"
            )
            return
        self._stack.pop()

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        return "\n".join(self._parts)

    def validate_closed(self) -> None:
        if self._fatal_error:
            raise ValueError(f"malformed html: {self._fatal_error}")
        if self._stack:
            raise ValueError(f"malformed html: unclosed <{self._stack[-1]}> tag")


def parse_document(path: Path, source: DocumentSourceSpec, source_id: str) -> list[CanonicalElement]:
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise ValueError(f"document {source_id} is empty")
    fmt = source.format if isinstance(source.format, DocumentFormat) else DocumentFormat(str(source.format))
    if fmt == DocumentFormat.TXT:
        return _elements_from_blocks(raw.splitlines(), source_id, default_type="text")
    if fmt == DocumentFormat.MARKDOWN:
        return _parse_markdown(raw, source_id)
    if fmt == DocumentFormat.HTML:
        return _parse_html(raw, source_id)
    raise ValueError(f"unsupported document format: {source.format}")


def _parse_html(raw: str, source_id: str) -> list[CanonicalElement]:
    lower = raw.lower()
    if "<html" not in lower or "<body" not in lower:
        raise ValueError(f"html document {source_id} must contain <html> and <body> elements")
    parser = _StrictHTMLTextExtractor()
    try:
        parser.feed(raw)
        parser.close()
    except Exception as exc:
        raise ValueError(f"malformed html in {source_id}: {exc}") from exc
    parser.validate_closed()
    text = parser.text()
    if not text.strip():
        raise ValueError(f"html document {source_id} produced no extractable text")
    return _elements_from_blocks(text.splitlines(), source_id, default_type="text")


def _parse_markdown(raw: str, source_id: str) -> list[CanonicalElement]:
    elements: list[CanonicalElement] = []
    element_idx = 0
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            content = stripped[level:].strip()
            element_type = "heading"
        else:
            content = stripped
            element_type = "text"
        element_idx += 1
        elements.append(
            CanonicalElement(
                element_id=f"{source_id}:e{element_idx}",
                element_type=element_type,
                content=content,
                source_document_id=source_id,
            )
        )
    if not elements:
        raise ValueError(f"markdown document {source_id} produced no elements")
    return elements


def _elements_from_blocks(
    lines: list[str],
    source_id: str,
    *,
    default_type: str,
) -> list[CanonicalElement]:
    elements: list[CanonicalElement] = []
    buffer: list[str] = []
    element_idx = 0

    def flush() -> None:
        nonlocal element_idx
        text = " ".join(buffer).strip()
        buffer.clear()
        if not text:
            return
        element_idx += 1
        elements.append(
            CanonicalElement(
                element_id=f"{source_id}:e{element_idx}",
                element_type=default_type,
                content=text,
                source_document_id=source_id,
            )
        )

    for line in lines:
        if not line.strip():
            flush()
            continue
        buffer.append(line.strip())
    flush()
    if not elements:
        raise ValueError(f"document {source_id} produced no elements")
    return elements


def load_documents_from_glob(root: Path, source: DocumentSourceSpec) -> list[tuple[Path, str]]:
    pattern = source.uri_pattern or "*"
    paths = sorted(root.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"no files for pattern {pattern} under {root}")
    docs: list[tuple[Path, str]] = []
    for path in paths:
        if not path.is_file():
            continue
        source_id = re.sub(r"[^a-zA-Z0-9._-]+", "_", path.stem)
        docs.append((path, source_id))
    if not docs:
        raise FileNotFoundError(f"no readable files for {pattern}")
    return docs
