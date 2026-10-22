"""Operational acceptance: structured profile offline ingest."""

from pathlib import Path

from src.compatibility.fraud.profile import load_fraud_profile
from src.compatibility.structured.ingest import ingest_structured_batch, read_batch_glob
from src.compatibility.structured.promotion import promote_structured_artifact
from src.compatibility.structured.transform import transform_structured_batch
from src.dataops.domain.artifact import ArtifactState
from src.dataops.domain.lineage import LineageOperation
from src.dataops.domain.promotion import PromotionStatus
from src.dataops.integrations.local import LocalBackend


def test_structured_profile_offline_smoke(tmp_path: Path) -> None:
    profile = load_fraud_profile()
    root = Path(__file__).resolve().parents[2]
    df = read_batch_glob(root, profile.source("batch_csv"))
    backend = LocalBackend.create(tmp_path)
    try:
        version_id = "v-structured-smoke"
        bronze = ingest_structured_batch(
            backend,
            profile,
            df,
            dataset_name="bronze",
            version_id=version_id,
            run_id="run-structured-smoke",
            source_artifact_id="source.batch_csv",
        )
        assert bronze["kernel_quality_report_id"]

        silver = transform_structured_batch(
            backend,
            profile,
            df,
            source_dataset_name="bronze",
            target_dataset_name="silver",
            source_version=version_id,
            target_version=version_id,
            run_id="run-structured-smoke",
        )
        assert silver["kernel_dataset_id"] == profile.dataset("silver").catalog_table

        edges = backend.lineage_store.list_upstream(
            silver["kernel_artifact_id"],
            silver["kernel_artifact_version"],
        )
        assert any(edge.operation == LineageOperation.TRANSFORM for edge in edges)

        receipt = promote_structured_artifact(
            backend,
            artifact_id=silver["kernel_artifact_id"],
            version=silver["kernel_artifact_version"],
            run_id="run-structured-promote",
            correlation_id="corr-structured",
            promotion_root=tmp_path / "promotion",
        )
        assert receipt.status == PromotionStatus.COMMITTED
        published = backend.artifact_store.head(
            silver["kernel_artifact_id"],
            silver["kernel_artifact_version"],
        )
        assert published.state == ArtifactState.PUBLISHED
    finally:
        backend.close()
