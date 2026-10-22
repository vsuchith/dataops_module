"""LLMOps parser and embedding unit tests."""

from pathlib import Path

import pytest

from src.llmops.compatibility.embeddings import deterministic_embed, embed_elements
from src.llmops.compatibility.parsers import parse_document
from src.llmops.compatibility.specs import DocumentFormat, DocumentSourceSpec


def test_deterministic_embed_is_stable() -> None:
    first = deterministic_embed("hello corpus")
    second = deterministic_embed("hello corpus")
    assert first == second
    assert len(first) == 16


def test_deterministic_embed_rejects_empty() -> None:
    with pytest.raises(ValueError):
        deterministic_embed("   ")


def test_embed_elements_records_ids() -> None:
    records = embed_elements([("e1", "alpha"), ("e2", "beta")])
    assert len(records) == 2
    assert records[0]["element_id"] == "e1"


def test_parse_markdown_fixture(tmp_path: Path) -> None:
    path = tmp_path / "sample.md"
    path.write_text("# Title\n\nBody paragraph.\n", encoding="utf-8")
    source = DocumentSourceSpec(name="md", format=DocumentFormat.MARKDOWN, uri_pattern="*.md")
    elements = parse_document(path, source, "sample")
    assert any(e.element_type == "heading" for e in elements)
    assert any(e.element_type == "text" for e in elements)


def test_parse_empty_txt_rejected(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("   \n", encoding="utf-8")
    source = DocumentSourceSpec(name="txt", format=DocumentFormat.TXT, uri_pattern="*.txt")
    with pytest.raises(ValueError, match="empty"):
        parse_document(path, source, "empty")


def test_parse_empty_markdown_rejected(tmp_path: Path) -> None:
    path = tmp_path / "empty.md"
    path.write_text("\n\n", encoding="utf-8")
    source = DocumentSourceSpec(name="md", format=DocumentFormat.MARKDOWN, uri_pattern="*.md")
    with pytest.raises(ValueError, match="empty"):
        parse_document(path, source, "empty")


def test_parse_malformed_html_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.html"
    path.write_text("<html><body><p>text<div></body></html>", encoding="utf-8")
    source = DocumentSourceSpec(name="html", format=DocumentFormat.HTML, uri_pattern="*.html")
    with pytest.raises(ValueError, match="malformed html"):
        parse_document(path, source, "bad")


def test_parse_html_without_body_rejected(tmp_path: Path) -> None:
    path = tmp_path / "nobody.html"
    path.write_text("<html><head></head></html>", encoding="utf-8")
    source = DocumentSourceSpec(name="html", format=DocumentFormat.HTML, uri_pattern="*.html")
    with pytest.raises(ValueError, match="must contain <html> and <body>"):
        parse_document(path, source, "nobody")
