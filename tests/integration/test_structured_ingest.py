"""Integration test: profile-driven structured ingest (offline)."""

from pathlib import Path

from src.compatibility.fraud.profile import load_fraud_profile
from src.compatibility.structured.ingest import ingest_structured_batch, read_batch_glob
from src.dataops.domain.dataset import DatasetModality
from src.dataops.domain.lineage import LineageOperation
from src.dataops.integrations.local import LocalBackend


def test_profile_csv_to_kernel_artifact(tmp_path: Path) -> None:
    profile = load_fraud_profile()
    csv_source = profile.source("batch_csv")
    root = Path(__file__).resolve().parents[2]
    df = read_batch_glob(root, csv_source)

    backend = LocalBackend.create(tmp_path)
    try:
        bronze = profile.dataset("bronze")
        result = ingest_structured_batch(
            backend,
            profile,
            df,
            dataset_name="bronze",
            version_id="v1",
            run_id="run-structured-integration",
            source_artifact_id=f"source.{csv_source.name}",
        )
        assert result["kernel_artifact_id"] == f"dataset.{bronze.name}"
        assert result["kernel_dataset_id"] == bronze.catalog_table
        assert result["kernel_quality_report_id"]

        stored, content = backend.artifact_store.get(result["kernel_artifact_id"], "v1")
        assert stored.kind.value == "structured_table"
        assert stored.media_type == "text/csv"
        assert stored.metadata["row_count"] == str(len(df))
        assert len(content) > 0

        dataset_version = backend.dataset_catalog.get(
            result["kernel_dataset_id"],
            result["kernel_dataset_version"],
        )
        assert dataset_version.modality == DatasetModality.STRUCTURED
        assert dataset_version.quality_report_id == result["kernel_quality_report_id"]
        assert dataset_version.physical_artifact_ids == [result["kernel_artifact_id"]]

        upstream = backend.lineage_store.list_upstream(
            result["kernel_artifact_id"],
            result["kernel_artifact_version"],
        )
        assert len(upstream) == 1
        edge = upstream[0]
        assert edge.operation == LineageOperation.INGEST
        assert edge.run_id == "run-structured-integration"
        assert edge.source_artifact_id == f"source.{csv_source.name}"
    finally:
        backend.close()
