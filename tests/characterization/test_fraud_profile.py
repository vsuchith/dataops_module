"""Fraud profile parity with legacy configuration."""

import pytest

from src.compatibility.fraud.api import validate_transaction
from src.compatibility.fraud.mlops_bridge import mlops_settings_snapshot
from src.compatibility.fraud.profile import load_fraud_profile
from src.core.config import MLOpsSettings
from src.mlops.pipelines.mlops_bronze import load_bronze_sources_config


def test_profile_settings_parity() -> None:
    profile = load_fraud_profile()
    legacy = MLOpsSettings()
    snap = mlops_settings_snapshot(profile)
    assert snap["bronze_table"] == legacy.bronze_table
    assert snap["feature_service"] == legacy.feature_service


def test_bronze_config_uses_profile_by_default(monkeypatch) -> None:
    monkeypatch.delenv("BRONZE_TABLES", raising=False)
    monkeypatch.delenv("FRAUD_PROFILE_DISABLED", raising=False)
    config = load_bronze_sources_config()
    assert config.get("profile_id") == "fraud_detection"
    table = config["sources"][0]["tables"][0]["bronze_table"]
    assert table.endswith("bronze.fraud_transactions")


def test_api_validate_transaction_via_profile() -> None:
    txn = {
        "transaction_id": "TXN_TEST",
        "amount": 100.0,
        "customer_id": "CUST_1",
    }
    result = validate_transaction(txn)
    assert result["transaction_id"] == "TXN_TEST"


def test_api_validate_transaction_missing_pk_raises() -> None:
    with pytest.raises(ValueError, match="transaction_id"):
        validate_transaction({"amount": 1.0, "customer_id": "CUST_1"})
