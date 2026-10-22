"""Structured dataset transforms via the DataOps kernel."""

from __future__ import annotations

from typing import Callable, Optional

import pandas as pd

from src.compatibility.structured.ingest import (
    materialize_batch_artifact,
    register_structured_dataset,
    structured_artifact_id,
)
from src.compatibility.structured.specs import StructuredProfile
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.integrations.local import LocalBackend


def transform_structured_batch(
    backend: LocalBackend,
    profile: StructuredProfile,
    df: pd.DataFrame,
    *,
    source_dataset_name: str,
    target_dataset_name: str,
    source_version: str,
    target_version: str,
    run_id: str,
    transform: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
) -> dict[str, str]:
    """Materialize a transformed table version with TRANSFORM lineage."""
    source_dataset = profile.dataset(source_dataset_name)
    target_dataset = profile.dataset(target_dataset_name)
    transformed = transform(df) if transform is not None else df.copy()

    artifact_ref = materialize_batch_artifact(
        backend.artifact_store,
        artifact_id=structured_artifact_id(target_dataset),
        version=target_version,
        df=transformed,
        producer_run_id=run_id,
    )
    _, content = backend.artifact_store.get(artifact_ref.artifact_id, artifact_ref.version)
    quality = backend.quality_evaluator.evaluate(artifact_ref, content)
    dataset_version = register_structured_dataset(
        backend,
        profile,
        dataset_name=target_dataset_name,
        artifact_ref=artifact_ref,
        version_id=target_version,
        quality_report_id=quality.report_id,
    )
    backend.lineage_store.record_edge(
        LineageEdge(
            source_artifact_id=structured_artifact_id(source_dataset),
            source_version=source_version,
            target_artifact_id=artifact_ref.artifact_id,
            target_version=artifact_ref.version,
            operation=LineageOperation.TRANSFORM,
            run_id=run_id,
            metadata={"profile_id": profile.profile_id},
        )
    )
    return {
        "kernel_artifact_id": artifact_ref.artifact_id,
        "kernel_artifact_version": artifact_ref.version,
        "kernel_dataset_id": dataset_version.dataset_id,
        "kernel_dataset_version": dataset_version.version_id,
        "kernel_quality_report_id": quality.report_id,
    }
