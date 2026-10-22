"""Fraud profile loading tests."""

from pathlib import Path

import pytest

from src.compatibility.fraud.profile import load_fraud_profile
from src.compatibility.fraud.mlops_bridge import bronze_sources_from_profile, mlops_settings_snapshot
from src.core.config import MLOpsSettings, TRINO_CATALOG
from src.mlops.pipelines.mlops_bronze import load_bronze_sources_config


def test_load_fraud_profile() -> None:
    profile = load_fraud_profile()
    assert profile.profile_id == "fraud_detection"
    assert len(profile.sources) >= 2
    assert len(profile.cdc_sources) == 1
    bronze = profile.dataset("bronze")
    assert bronze.primary_key == "transaction_id"
    assert bronze.label_column == "is_fraudulent"
    assert bronze.schema_ref == "schema://fraud/transactions/v1"
    assert profile.lakefs.bronze_repository == "bronze"
    assert len(profile.quality_checks) >= 2
    assert profile.promotion_policy.require_quality_pass is True


def test_profile_matches_legacy_settings() -> None:
    profile = load_fraud_profile()
    legacy = MLOpsSettings()
    snapshot = mlops_settings_snapshot(profile)
    assert snapshot["bronze_table"] == legacy.bronze_table
    assert snapshot["silver_table"] == legacy.silver_table
    assert snapshot["gold_table"] == legacy.gold_table
    assert snapshot["primary_key"] == legacy.primary_key
    assert snapshot["label_column"] == legacy.label_column
    assert snapshot["mlflow_experiment"] == legacy.mlflow_experiment
    assert snapshot["streaming_source_topic"] == legacy.streaming_source_topic


def test_bronze_sources_from_profile() -> None:
    root = Path(__file__).resolve().parents[3]
    profile_path = root / "profiles" / "fraud_detection" / "profile.yaml"
    config = bronze_sources_from_profile(profile_path)
    table = config["sources"][0]["tables"][0]
    assert table["bronze_table"] == f"{TRINO_CATALOG}.bronze.fraud_transactions"
    assert "parquet" in table["source_path"] or "data" in table["source_path"]
    assert config["sources"][0]["lakefs_repository"] == "bronze"
    assert config["sources"][0]["lakefs_branch"] == "dev"


def test_broken_explicit_profile_fails_closed(monkeypatch) -> None:
    monkeypatch.delenv("BRONZE_TABLES", raising=False)
    monkeypatch.delenv("FRAUD_PROFILE_DISABLED", raising=False)
    monkeypatch.setenv("FRAUD_PROFILE_PATH", "/nonexistent/broken/profile.yaml")
    with pytest.raises(FileNotFoundError):
        load_bronze_sources_config()
