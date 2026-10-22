"""Offline batch and CDC ingest helpers using profile specs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.compatibility.structured.specs import (
    BatchFormat,
    CdcSourceSpec,
    DatasetSpec,
    SourceSpec,
    StructuredProfile,
)
from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState
from src.dataops.domain.dataset import DatasetModality, DatasetVersion
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore


def read_batch_file(path: Path, source: SourceSpec) -> pd.DataFrame:
    fmt = source.format if isinstance(source.format, BatchFormat) else BatchFormat(str(source.format))
    if fmt == BatchFormat.CSV:
        return pd.read_csv(path)
    if fmt == BatchFormat.PARQUET:
        return pd.read_parquet(path)
    raise ValueError(f"unsupported batch format: {source.format}")


def read_batch_glob(root: Path, source: SourceSpec) -> pd.DataFrame:
    pattern = source.uri_pattern or "*"
    paths = sorted(root.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"no files for pattern {pattern} under {root}")
    frames = [read_batch_file(p, source) for p in paths if p.is_file()]
    if not frames:
        raise FileNotFoundError(f"no readable files for {pattern}")
    return pd.concat(frames, ignore_index=True)


def parse_cdc_event(payload: str | bytes, spec: CdcSourceSpec) -> dict[str, Any]:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("cdc event must be a JSON object")
    if spec.primary_key not in data:
        raise ValueError(f"cdc event missing primary key {spec.primary_key}")
    return data


def structured_artifact_id(dataset: DatasetSpec) -> str:
    return f"dataset.{dataset.name}"


def structured_dataset_id(dataset: DatasetSpec) -> str:
    return dataset.catalog_table


def batch_version_id(df: pd.DataFrame) -> str:
    """Content-addressed batch version for idempotent re-runs."""
    content = df.to_csv(index=False).encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()[:16]
    return f"v-{digest}"


def materialize_batch_artifact(
    store: LocalFilesystemArtifactStore,
    *,
    artifact_id: str,
    version: str,
    df: pd.DataFrame,
    producer_run_id: Optional[str] = None,
) -> ArtifactRef:
    content = df.to_csv(index=False).encode("utf-8")
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id=artifact_id,
        version=version,
        kind=ArtifactKind.STRUCTURED_TABLE,
        uri=f"file:///{artifact_id}/{version}",
        checksum=checksum,
        state=ArtifactState.VALIDATED,
        media_type="text/csv",
        producer_run_id=producer_run_id,
        metadata={"row_count": str(len(df))},
    )
    return store.put(ref, content)


def register_structured_dataset(
    backend: LocalBackend,
    profile: StructuredProfile,
    *,
    dataset_name: str,
    artifact_ref: ArtifactRef,
    version_id: str,
    quality_report_id: Optional[str] = None,
) -> DatasetVersion:
    dataset = profile.dataset(dataset_name)
    version = DatasetVersion(
        dataset_id=structured_dataset_id(dataset),
        version_id=version_id,
        modality=DatasetModality.STRUCTURED,
        physical_artifact_ids=[artifact_ref.artifact_id],
        schema_or_manifest_ref=dataset.schema_ref,
        quality_report_id=quality_report_id,
    )
    return backend.dataset_catalog.register(version)


def record_structured_lineage(
    backend: LocalBackend,
    *,
    profile: StructuredProfile,
    source_artifact_id: str,
    source_version: str,
    target_ref: ArtifactRef,
    run_id: str,
) -> LineageEdge:
    edge = LineageEdge(
        source_artifact_id=source_artifact_id,
        source_version=source_version,
        target_artifact_id=target_ref.artifact_id,
        target_version=target_ref.version,
        operation=LineageOperation.INGEST,
        run_id=run_id,
        metadata={"profile_id": profile.profile_id},
    )
    return backend.lineage_store.record_edge(edge)


def ingest_structured_batch(
    backend: LocalBackend,
    profile: StructuredProfile,
    df: pd.DataFrame,
    *,
    dataset_name: str,
    version_id: str,
    run_id: str,
    source_artifact_id: str = "structured.raw.batch",
    source_version: str = "v0",
) -> dict[str, str]:
    dataset = profile.dataset(dataset_name)
    artifact_ref = materialize_batch_artifact(
        backend.artifact_store,
        artifact_id=structured_artifact_id(dataset),
        version=version_id,
        df=df,
        producer_run_id=run_id,
    )
    _, content = backend.artifact_store.get(artifact_ref.artifact_id, artifact_ref.version)
    quality = backend.quality_evaluator.evaluate(artifact_ref, content)
    dataset_version = register_structured_dataset(
        backend,
        profile,
        dataset_name=dataset_name,
        artifact_ref=artifact_ref,
        version_id=version_id,
        quality_report_id=quality.report_id,
    )
    record_structured_lineage(
        backend,
        profile=profile,
        source_artifact_id=source_artifact_id,
        source_version=source_version,
        target_ref=artifact_ref,
        run_id=run_id,
    )
    return {
        "kernel_artifact_id": artifact_ref.artifact_id,
        "kernel_artifact_version": artifact_ref.version,
        "kernel_dataset_id": dataset_version.dataset_id,
        "kernel_dataset_version": dataset_version.version_id,
        "kernel_quality_report_id": quality.report_id,
    }


def ingest_structured_batch_from_dataframe(
    df: pd.DataFrame,
    *,
    profile: StructuredProfile,
    dataset_name: str,
    run_id: str,
    version_id: Optional[str] = None,
    backend_root: Optional[Path] = None,
    source_artifact_id: str = "structured.raw.batch",
    source_version: str = "v0",
) -> dict[str, str]:
    resolved_version = version_id or batch_version_id(df)
    backend = LocalBackend.create(backend_root)
    try:
        return ingest_structured_batch(
            backend,
            profile,
            df,
            dataset_name=dataset_name,
            version_id=resolved_version,
            run_id=run_id,
            source_artifact_id=source_artifact_id,
            source_version=source_version,
        )
    finally:
        backend.close()
