"""Operational acceptance: reference corpus local-lite path (E4)."""

import json
from pathlib import Path

from src.dataops.domain.lineage import LineageOperation
from src.dataops.integrations.local import LocalBackend
from src.llmops.compatibility.corpus import load_profile_documents, run_corpus_pipeline
from src.llmops.compatibility.handoff import CorpusVersionRef
from src.llmops.compatibility.quality_store import load_quality_report
from src.llmops.compatibility.settings_bridge import load_reference_corpus_profile


def test_reference_corpus_operational_path(tmp_path: Path) -> None:
    profile = load_reference_corpus_profile()
    root = Path(__file__).resolve().parents[2]
    documents = load_profile_documents(root, profile)

    result = run_corpus_pipeline(
        profile,
        documents,
        run_id="run-llmops-operational",
        backend_root=tmp_path,
    )

    backend = LocalBackend.create(tmp_path)
    try:
        version_id = result["corpus_version_id"]
        corpus_id = "ref.corpus.demo"
        _, handoff_bytes = backend.artifact_store.get(
            f"{corpus_id}.corpus_version_ref",
            version_id,
        )
        handoff = CorpusVersionRef.model_validate(json.loads(handoff_bytes.decode("utf-8")))
        assert handoff.corpus_id == corpus_id
        assert handoff.schema_version == "1.0.0"
        assert handoff.index_ref is not None
        assert handoff.embedding_set_refs
        assert handoff.security_labels == ["internal"]

        for report_id_key in (
            "kernel_quality_report_id",
            "embedding_quality_report_id",
            "index_quality_report_id",
        ):
            report_id = result[report_id_key]
            report = load_quality_report(backend, report_id, version_id)
            assert report.report_id == report_id
            assert report.checks

        index_ref, index_bytes = backend.artifact_store.get(
            f"{corpus_id}.reference_index",
            version_id,
        )
        index_payload = json.loads(index_bytes.decode("utf-8"))
        assert index_payload["entry_count"] == int(result["index_entry_count"])
        assert index_ref.metadata["entry_count"] == result["index_entry_count"]

        handoff_edges = backend.lineage_store.list_upstream(
            f"{corpus_id}.corpus_version_ref",
            version_id,
        )
        assert len(handoff_edges) == 1
        assert handoff_edges[0].source_artifact_id == f"{corpus_id}.reference_index"

        embed_edges = backend.lineage_store.list_upstream(
            f"{corpus_id}.embeddings",
            version_id,
        )
        assert len(embed_edges) == 1
        assert embed_edges[0].operation == LineageOperation.EMBED
        assert embed_edges[0].source_artifact_id == f"{corpus_id}.element_set"

        index_edges = backend.lineage_store.list_upstream(
            f"{corpus_id}.reference_index",
            version_id,
        )
        assert len(index_edges) == 1
        assert index_edges[0].operation == LineageOperation.INDEX
        assert index_edges[0].source_artifact_id == f"{corpus_id}.embeddings"

        finetune_ref, finetune_bytes = backend.artifact_store.get(
            f"{corpus_id}.finetuning",
            version_id,
        )
        assert finetune_ref.media_type == "application/x-ndjson"
        assert len(finetune_bytes.splitlines()) == int(result["training_samples"])

        finetune_edges = backend.lineage_store.list_upstream(
            f"{corpus_id}.finetuning",
            version_id,
        )
        assert len(finetune_edges) == 1
        assert finetune_edges[0].operation == LineageOperation.TRANSFORM
    finally:
        backend.close()
