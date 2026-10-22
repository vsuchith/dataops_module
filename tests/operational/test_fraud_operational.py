"""Operational acceptance: fraud profile compatibility path."""

from pathlib import Path

from src.compatibility.fraud.profile import load_fraud_profile
from src.compatibility.fraud.smoke import offline_train_serve_smoke
from src.compatibility.structured.ingest import read_batch_glob
from src.dataops.integrations.local import LocalBackend


def test_fraud_profile_representative_smoke(tmp_path: Path) -> None:
    profile = load_fraud_profile()
    assert profile.promotion_policy.require_quality_pass is True
    root = Path(__file__).resolve().parents[2]
    df = read_batch_glob(root, profile.source("batch_csv"))

    backend = LocalBackend.create(tmp_path)
    try:
        result = offline_train_serve_smoke(
            backend,
            profile,
            df,
            version_id="v-fraud-smoke",
            run_id="run-fraud-smoke",
        )
        assert result["bronze"]["kernel_artifact_id"]
        assert result["silver"]["kernel_dataset_id"] == profile.dataset("silver").catalog_table
        assert result["gold"]["kernel_dataset_id"] == profile.dataset("gold").catalog_table
        assert result["model_artifact_id"] == f"model.{profile.mlflow.model_name}"
        assert "fraud_score" in result["prediction"]
        assert "is_fraudulent" in result["prediction"]
    finally:
        backend.close()
