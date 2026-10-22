"""Bridge fraud profile to legacy MLOps configuration shapes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.compatibility.fraud.profile import FraudDetectionProfile, load_fraud_profile
from src.core.config import TRINO_CATALOG


def bronze_sources_from_profile(profile_path: str | Path) -> dict[str, Any]:
    """Produce mlops_bronze-compatible sources dict from profile YAML."""
    profile = load_fraud_profile(profile_path)
    bronze = profile.dataset("bronze")
    batch_source = profile.source(bronze.source_ref) if bronze.source_ref else profile.sources[0]
    return {
        "sources": [
            {
                "name": profile.profile_id,
                "lakefs_repository": profile.lakefs.bronze_repository,
                "lakefs_branch": profile.lakefs.dev_branch,
                "tables": [
                    {
                        "bronze_table": profile.bronze_table_fqn(TRINO_CATALOG),
                        "source_path": batch_source.uri_pattern,
                        "description": f"From profile {profile.profile_id}",
                        "primary_key": bronze.primary_key,
                        "label_column": bronze.label_column,
                    }
                ],
            }
        ],
        "profile_id": profile.profile_id,
        "profile_version": profile.version,
    }


def mlops_settings_snapshot(profile: FraudDetectionProfile) -> dict[str, str]:
    """Key fields that must match legacy MLOpsSettings defaults."""
    bronze = profile.dataset("bronze")
    silver = profile.dataset("silver")
    gold = profile.dataset("gold")
    cdc = profile.cdc_sources[0] if profile.cdc_sources else None
    return {
        "bronze_table": bronze.catalog_table.split(".")[-1],
        "silver_table": silver.catalog_table.split(".")[-1],
        "gold_table": gold.catalog_table.split(".")[-1],
        "primary_key": bronze.primary_key,
        "label_column": bronze.label_column or "",
        "mlflow_experiment": profile.mlflow.experiment,
        "mlflow_model_name": profile.mlflow.model_name,
        "feature_service": profile.feast.feature_service,
        "streaming_source_topic": cdc.topic if cdc else "",
    }


def validate_transaction_payload(
    profile: FraudDetectionProfile, payload: dict[str, Any]
) -> None:
    """Validate API transaction dict against profile schema keys."""
    bronze = profile.dataset("bronze")
    if bronze.primary_key not in payload:
        raise ValueError(f"missing primary key {bronze.primary_key}")
