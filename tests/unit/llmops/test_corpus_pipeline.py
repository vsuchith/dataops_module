"""LLMOps handoff model unit tests."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from src.llmops.compatibility.corpus import load_profile_documents, run_corpus_pipeline
from src.llmops.compatibility.corpus_quality import CorpusQualityError
from src.llmops.compatibility.handoff import CorpusVersionRef, HandoffValidationError, parse_handoff_contract
from src.llmops.compatibility.quality_store import load_quality_report
from src.llmops.compatibility.settings_bridge import load_reference_corpus_profile
from src.llmops.compatibility.specs import DocumentFormat, DocumentSourceSpec
from src.dataops.domain.dataset import DatasetModality
from src.dataops.domain.lineage import LineageOperation
from src.dataops.integrations.local import LocalBackend


def test_reference_corpus_profile_loads() -> None:
    profile = load_reference_corpus_profile()
    corpus = profile.dataset("corpus")
    assert corpus.corpus_id == "ref.corpus.demo"


def test_corpus_version_ref_fixture_contract() -> None:
    payload = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "contract"
            / "fixtures"
            / "valid"
            / "corpus_version_ref.json"
        ).read_text(encoding="utf-8")
    )
    model = parse_handoff_contract("corpus_version_ref", payload)
    assert isinstance(model, CorpusVersionRef)
    assert model.schema_version == "1.0.0"


def test_corpus_version_ref_rejects_unsupported_schema() -> None:
    payload = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "contract"
            / "fixtures"
            / "invalid"
            / "corpus_version_ref_unsupported_schema.json"
        ).read_text(encoding="utf-8")
    )
    with pytest.raises(HandoffValidationError, match="unsupported handoff schema_version"):
        parse_handoff_contract("corpus_version_ref", payload)


def test_run_corpus_pipeline_persists_kernel_state(tmp_path: Path) -> None:
    profile = load_reference_corpus_profile()
    root = Path(__file__).resolve().parents[3]
    documents = load_profile_documents(root, profile)

    result = run_corpus_pipeline(
        profile,
        documents,
        run_id="run-llmops-unit",
        backend_root=tmp_path,
    )

    backend = LocalBackend.create(tmp_path)
    try:
        version_id = result["corpus_version_id"]
        assert int(result["document_count"]) >= 3
        assert int(result["element_count"]) > 0
        assert int(result["embedding_count"]) > 0
        assert int(result["training_samples"]) > 0

        dataset = backend.dataset_catalog.get("ref.corpus.demo", version_id)
        assert dataset.modality == DatasetModality.TEXT_CORPUS
        assert dataset.quality_report_id

        loaded_quality = load_quality_report(
            backend,
            dataset.quality_report_id,
            version_id,
        )
        assert loaded_quality.pass_fail is True
        datetime.fromisoformat(
            loaded_quality.evaluated_at.replace("Z", "+00:00")
        )

        corpus_id = profile.dataset("corpus").corpus_id
        handoff_upstream = backend.lineage_store.list_upstream(
            f"{corpus_id}.corpus_version_ref",
            version_id,
        )
        assert len(handoff_upstream) == 1
        assert handoff_upstream[0].operation == LineageOperation.INGEST
        assert handoff_upstream[0].source_artifact_id == f"{corpus_id}.reference_index"

        embed_upstream = backend.lineage_store.list_upstream(
            f"{corpus_id}.embeddings",
            version_id,
        )
        assert len(embed_upstream) == 1
        assert embed_upstream[0].operation == LineageOperation.EMBED

        index_upstream = backend.lineage_store.list_upstream(
            f"{corpus_id}.reference_index",
            version_id,
        )
        assert len(index_upstream) == 1
        assert index_upstream[0].operation == LineageOperation.INDEX
    finally:
        backend.close()


def test_run_corpus_pipeline_is_idempotent_on_rerun(tmp_path: Path) -> None:
    profile = load_reference_corpus_profile()
    root = Path(__file__).resolve().parents[3]
    documents = load_profile_documents(root, profile)

    first = run_corpus_pipeline(
        profile,
        documents,
        run_id="run-llmops-idempotent",
        backend_root=tmp_path,
    )
    second = run_corpus_pipeline(
        profile,
        documents,
        run_id="run-llmops-idempotent",
        version_id=first["corpus_version_id"],
        backend_root=tmp_path,
    )
    assert second["corpus_version_id"] == first["corpus_version_id"]
    assert second["element_count"] == first["element_count"]
    assert second["embedding_count"] == first["embedding_count"]


def test_run_corpus_pipeline_rerun_with_new_run_id(tmp_path: Path) -> None:
    profile = load_reference_corpus_profile()
    root = Path(__file__).resolve().parents[3]
    documents = load_profile_documents(root, profile)

    first = run_corpus_pipeline(
        profile,
        documents,
        run_id="review-run-1",
        backend_root=tmp_path,
    )
    second = run_corpus_pipeline(
        profile,
        documents,
        run_id="review-run-2",
        version_id=first["corpus_version_id"],
        backend_root=tmp_path,
    )
    assert second["corpus_version_id"] == first["corpus_version_id"]

    backend = LocalBackend.create(tmp_path)
    try:
        version_id = first["corpus_version_id"]
        handoff_edges = backend.lineage_store.list_upstream(
            "ref.corpus.demo.corpus_version_ref",
            version_id,
        )
        run_ids = {edge.run_id for edge in handoff_edges}
        assert "review-run-1" in run_ids
        assert "review-run-2" in run_ids
    finally:
        backend.close()


def test_duplicate_source_id_rejected(tmp_path: Path) -> None:
    profile = load_reference_corpus_profile()
    path = tmp_path / "dup.md"
    path.write_text("# Title\n\nDuplicate body.\n", encoding="utf-8")
    source = DocumentSourceSpec(name="md", format=DocumentFormat.MARKDOWN, uri_pattern="*.md")
    documents = [(path, "dup_doc", source), (path, "dup_doc", source)]

    with pytest.raises(CorpusQualityError, match="unique_source_ids"):
        run_corpus_pipeline(
            profile,
            documents,
            run_id="run-duplicate-source",
            backend_root=tmp_path,
        )


def test_duplicate_checksum_rejected(tmp_path: Path) -> None:
    profile = load_reference_corpus_profile()
    path = tmp_path / "shared.md"
    path.write_text("# Shared\n\nSame bytes.\n", encoding="utf-8")
    source = DocumentSourceSpec(name="md", format=DocumentFormat.MARKDOWN, uri_pattern="*.md")
    documents = [(path, "copy_a", source), (path, "copy_b", source)]

    with pytest.raises(CorpusQualityError, match="unique_document_checksums"):
        run_corpus_pipeline(
            profile,
            documents,
            run_id="run-duplicate-checksum",
            backend_root=tmp_path,
        )
