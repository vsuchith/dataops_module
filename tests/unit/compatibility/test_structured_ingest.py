"""Structured ingest unit tests."""

import json
from pathlib import Path

import pytest

from src.compatibility.fraud.profile import load_fraud_profile
from src.compatibility.structured.ingest import (
    materialize_batch_artifact,
    parse_cdc_event,
    read_batch_glob,
)
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore


def test_csv_batch_ingest_from_fixture() -> None:
    profile = load_fraud_profile()
    csv_source = profile.source("batch_csv")
    root = Path(__file__).resolve().parents[3]
    df = read_batch_glob(root, csv_source)
    assert len(df) == 3
    assert "transaction_id" in df.columns


def test_cdc_event_shape() -> None:
    profile = load_fraud_profile()
    cdc = profile.cdc_source("fraud_transactions_cdc")
    event = parse_cdc_event(
        json.dumps({"transaction_id": "TXN_1", "amount": 10}),
        cdc,
    )
    assert event["transaction_id"] == "TXN_1"


def test_cdc_event_missing_pk_raises() -> None:
    profile = load_fraud_profile()
    cdc = profile.cdc_source("fraud_transactions_cdc")
    with pytest.raises(ValueError):
        parse_cdc_event(json.dumps({"amount": 10}), cdc)


def test_cdc_event_non_object_raises() -> None:
    profile = load_fraud_profile()
    cdc = profile.cdc_source("fraud_transactions_cdc")
    with pytest.raises(ValueError, match="JSON object"):
        parse_cdc_event(json.dumps(["not", "an", "object"]), cdc)


def test_materialize_batch_artifact(tmp_path: Path) -> None:
    profile = load_fraud_profile()
    csv_source = profile.source("batch_csv")
    root = Path(__file__).resolve().parents[3]
    df = read_batch_glob(root, csv_source)
    store = LocalFilesystemArtifactStore(tmp_path)
    ref = materialize_batch_artifact(
        store,
        artifact_id="fraud.transactions",
        version="v-test",
        df=df,
    )
    assert ref.metadata["row_count"] == "3"
