"""Offline fraud train/serve smoke through compatibility boundaries."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd

from src.compatibility.fraud.api import validate_transaction
from src.compatibility.fraud.profile import FraudDetectionProfile
from src.compatibility.structured.ingest import ingest_structured_batch
from src.compatibility.structured.transform import transform_structured_batch
from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore


def _deterministic_model_weights(df: pd.DataFrame, label_column: str) -> dict[str, Any]:
    labels = df[label_column].astype(int).tolist() if label_column in df.columns else []
    fraud_rate = sum(labels) / len(labels) if labels else 0.0
    return {
        "model_name": "fraud-detector-stub",
        "fraud_rate": fraud_rate,
        "training_rows": len(df),
        "weights_digest": hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()[:16],
    }


def train_fraud_model_stub(
    backend: LocalBackend,
    profile: FraudDetectionProfile,
    gold_df: pd.DataFrame,
    *,
    version_id: str,
    run_id: str,
) -> ArtifactRef:
    gold = profile.dataset("gold")
    weights = _deterministic_model_weights(gold_df, gold.label_column or "is_fraudulent")
    content = json.dumps(weights, sort_keys=True).encode("utf-8")
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id=f"model.{profile.mlflow.model_name}",
        version=version_id,
        kind=ArtifactKind.MODEL,
        uri=f"file:///models/{profile.mlflow.model_name}/{version_id}",
        checksum=checksum,
        state=ArtifactState.VALIDATED,
        media_type="application/json",
        producer_run_id=run_id,
        metadata={"profile_id": profile.profile_id},
    )
    stored = backend.artifact_store.put(ref, content)
    backend.lineage_store.record_edge(
        LineageEdge(
            source_artifact_id=f"dataset.{gold.name}",
            source_version=version_id,
            target_artifact_id=stored.artifact_id,
            target_version=stored.version,
            operation=LineageOperation.TRAIN,
            run_id=run_id,
            metadata={"profile_id": profile.profile_id},
        )
    )
    return stored


def serve_fraud_prediction(
    profile: FraudDetectionProfile,
    model_ref: ArtifactRef,
    model_bytes: bytes,
    transaction: dict[str, Any],
) -> dict[str, Any]:
    validate_transaction(transaction)
    weights = json.loads(model_bytes.decode("utf-8"))
    bronze = profile.dataset("bronze")
    key = str(transaction[bronze.primary_key])
    score = (int(hashlib.sha256(key.encode()).hexdigest(), 16) % 1000) / 1000.0
    threshold = max(0.1, weights.get("fraud_rate", 0.05))
    return {
        "transaction_id": key,
        "fraud_score": score,
        "is_fraudulent": score >= threshold,
        "model_version": model_ref.version,
    }


def offline_train_serve_smoke(
    backend: LocalBackend,
    profile: FraudDetectionProfile,
    df: pd.DataFrame,
    *,
    version_id: str,
    run_id: str,
) -> dict[str, Any]:
    bronze = ingest_structured_batch(
        backend,
        profile,
        df,
        dataset_name="bronze",
        version_id=version_id,
        run_id=run_id,
    )
    silver = transform_structured_batch(
        backend,
        profile,
        df,
        source_dataset_name="bronze",
        target_dataset_name="silver",
        source_version=version_id,
        target_version=version_id,
        run_id=run_id,
    )
    gold = transform_structured_batch(
        backend,
        profile,
        df,
        source_dataset_name="silver",
        target_dataset_name="gold",
        source_version=version_id,
        target_version=version_id,
        run_id=run_id,
    )
    model_ref = train_fraud_model_stub(
        backend,
        profile,
        df,
        version_id=version_id,
        run_id=run_id,
    )
    _, model_bytes = backend.artifact_store.get(model_ref.artifact_id, model_ref.version)
    sample = df.iloc[0].to_dict()
    prediction = serve_fraud_prediction(profile, model_ref, model_bytes, sample)
    return {
        "bronze": bronze,
        "silver": silver,
        "gold": gold,
        "model_artifact_id": model_ref.artifact_id,
        "prediction": prediction,
    }
