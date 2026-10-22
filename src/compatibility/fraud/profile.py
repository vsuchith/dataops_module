"""Fraud detection profile — defaults migrated from MLOpsSettings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.compatibility.structured.specs import StructuredProfile


class LakefsProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bronze_repository: str = "bronze"
    warehouse_repository: str = "warehouse"
    dev_branch: str = "dev"
    main_branch: str = "main"


class MlflowProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment: str = "fraud-detection"
    model_name: str = "fraud-detector"


class FeastProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_service: str = "fraud_detection_v1"
    repo_path: str = "/app/feast_repo"


class FraudDetectionProfile(StructuredProfile):
    """Fraud profile extending generic structured specs."""

    lakefs: LakefsProfileConfig = Field(default_factory=LakefsProfileConfig)
    mlflow: MlflowProfileConfig = Field(default_factory=MlflowProfileConfig)
    feast: FeastProfileConfig = Field(default_factory=FeastProfileConfig)
    streaming_enabled: bool = True

    @model_validator(mode="after")
    def bronze_dataset_has_schema(self) -> FraudDetectionProfile:
        bronze = self.dataset("bronze")
        if not bronze.schema_ref:
            raise ValueError("bronze dataset requires schema_ref")
        return self

    def bronze_table_fqn(self, catalog: str) -> str:
        ds = self.dataset("bronze")
        if ds.catalog_table.count(".") >= 2:
            return ds.catalog_table
        return f"{catalog}.{ds.catalog_table}"

    def silver_table_fqn(self, catalog: str) -> str:
        ds = self.dataset("silver")
        if ds.catalog_table.count(".") >= 2:
            return ds.catalog_table
        return f"{catalog}.{ds.catalog_table}"

    def gold_table_fqn(self, catalog: str) -> str:
        ds = self.dataset("gold")
        if ds.catalog_table.count(".") >= 2:
            return ds.catalog_table
        if "." in ds.catalog_table:
            return f"{catalog}.{ds.catalog_table}"
        return f"{catalog}.gold.{ds.catalog_table}"


def default_profile_path() -> Path:
    return Path(__file__).resolve().parents[3] / "profiles" / "fraud_detection" / "profile.yaml"


def profile_is_explicitly_selected() -> bool:
    if os.getenv("FRAUD_PROFILE_DISABLED", "").lower() in ("1", "true", "yes"):
        return False
    if os.getenv("FRAUD_PROFILE_PATH"):
        return True
    return default_profile_path().exists()


def load_fraud_profile(path: Optional[Path | str] = None) -> FraudDetectionProfile:
    profile_path = Path(path) if path else default_profile_path()
    if not profile_path.exists():
        raise FileNotFoundError(f"fraud profile not found: {profile_path}")
    raw: dict[str, Any] = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    return FraudDetectionProfile.model_validate(raw)


def profile_path_from_env() -> Optional[Path]:
    explicit = os.getenv("FRAUD_PROFILE_PATH")
    if explicit:
        return Path(explicit)
    default = default_profile_path()
    return default if default.exists() else None
