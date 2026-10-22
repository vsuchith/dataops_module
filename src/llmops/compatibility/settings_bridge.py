"""Map inline reference corpus profile defaults to LLMOpsSettings."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.core.config import LLMOPS_CONFIG
from src.llmops.compatibility.specs import (
    CorpusDatasetSpec,
    DocumentFormat,
    DocumentSourceSpec,
    QualityCheckSpec,
    ReferenceCorpusProfile,
)


def default_reference_corpus_profile() -> ReferenceCorpusProfile:
    return ReferenceCorpusProfile(
        profile_id="reference_corpus",
        version="1.0.0",
        parser_profile="reference-txt-md-html-v1",
        sources=[
            DocumentSourceSpec(
                name="fixture_docs",
                format=DocumentFormat.MARKDOWN,
                uri_pattern="profiles/reference_corpus/fixtures/*.md",
                description="Markdown fixtures for offline tests",
            ),
            DocumentSourceSpec(
                name="fixture_txt",
                format=DocumentFormat.TXT,
                uri_pattern="profiles/reference_corpus/fixtures/*.txt",
            ),
            DocumentSourceSpec(
                name="fixture_html",
                format=DocumentFormat.HTML,
                uri_pattern="profiles/reference_corpus/fixtures/*.html",
            ),
        ],
        datasets=[
            CorpusDatasetSpec(
                name="corpus",
                corpus_id="ref.corpus.demo",
                artifact_id="llm.corpus.handoff",
                catalog_table="bronze.reference_corpus",
                source_ref="fixture_docs",
                schema_ref="schema://reference/corpus/v1",
            )
        ],
        quality_checks=[
            QualityCheckSpec(
                name="corpus_non_empty",
                severity="critical",
                rule="count(elements) > 0",
            ),
            QualityCheckSpec(
                name="unique_source_ids",
                severity="critical",
                rule="unique(document.source_id)",
            ),
            QualityCheckSpec(
                name="unique_document_checksums",
                severity="critical",
                rule="unique(document.checksum)",
            ),
            QualityCheckSpec(
                name="unique_element_ids",
                severity="critical",
                rule="unique(element.element_id)",
            ),
        ],
        security_labels=["internal"],
    )


def load_reference_corpus_profile(path: Path | None = None) -> ReferenceCorpusProfile:
    profile_path = path or (
        Path(__file__).resolve().parents[3] / "profiles" / "reference_corpus" / "profile.yaml"
    )
    if not profile_path.is_file():
        return default_reference_corpus_profile()
    raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    return ReferenceCorpusProfile.model_validate(raw)


def llmops_settings_snapshot(profile: ReferenceCorpusProfile) -> dict[str, str]:
    corpus = profile.dataset("corpus")
    return {
        "repo": str(LLMOPS_CONFIG["repo"]),
        "branch": str(LLMOPS_CONFIG["branch"]),
        "corpus_prefix": str(LLMOPS_CONFIG["corpus_prefix"]),
        "embedding_model": str(LLMOPS_CONFIG["embedding_model"]),
        "corpus_id": corpus.corpus_id,
        "catalog_table": corpus.catalog_table,
        "parser_profile": profile.parser_profile,
    }
