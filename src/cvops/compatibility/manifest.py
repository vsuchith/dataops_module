"""Manifest ingest via DataOps kernel ports (E3)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from src.cvops.compatibility.specs import CvopsProfile
from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState
from src.dataops.domain.dataset import DatasetModality, DatasetVersion
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore


def build_manifest_payload(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not entries:
        raise ValueError("manifest requires at least one image entry")
    return {
        "images": entries,
        "count": len(entries),
    }


def load_fixture_manifest(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    images = raw.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("fixture manifest must contain a non-empty images list")
    for image in images:
        if not isinstance(image, dict):
            raise ValueError("manifest image entries must be objects")
        if not image.get("image_id") or not image.get("original_path"):
            raise ValueError("manifest image entries require image_id and original_path")
    return images


def manifest_version_id(entries: list[dict[str, Any]]) -> str:
    """Content-addressed manifest version for idempotent re-runs."""
    payload = build_manifest_payload(entries)
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"v-{digest}"


def materialize_manifest_artifact(
    store: LocalFilesystemArtifactStore,
    *,
    artifact_id: str,
    version: str,
    entries: list[dict[str, Any]],
    producer_run_id: Optional[str] = None,
) -> ArtifactRef:
    payload = build_manifest_payload(entries)
    content = json.dumps(payload, sort_keys=True).encode("utf-8")
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id=artifact_id,
        version=version,
        kind=ArtifactKind.GENERIC,
        uri=f"file:///{artifact_id}/{version}",
        checksum=checksum,
        state=ArtifactState.VALIDATED,
        media_type="application/json",
        producer_run_id=producer_run_id,
        metadata={"image_count": str(len(entries))},
    )
    return store.put(ref, content)


def register_manifest_dataset(
    backend: LocalBackend,
    profile: CvopsProfile,
    *,
    artifact_ref: ArtifactRef,
    version_id: str,
    quality_report_id: Optional[str] = None,
) -> DatasetVersion:
    manifest = profile.dataset("manifest")
    version = DatasetVersion(
        dataset_id=manifest.dataset_id,
        version_id=version_id,
        modality=DatasetModality.IMAGE_COLLECTION,
        physical_artifact_ids=[artifact_ref.artifact_id],
        schema_or_manifest_ref=manifest.schema_ref,
        quality_report_id=quality_report_id,
    )
    return backend.dataset_catalog.register(version)


def record_manifest_lineage(
    backend: LocalBackend,
    *,
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
        metadata={"profile_id": "object_detection"},
    )
    return backend.lineage_store.record_edge(edge)


def ingest_manifest(
    backend: LocalBackend,
    profile: CvopsProfile,
    entries: list[dict[str, Any]],
    *,
    version_id: str,
    run_id: str,
    source_artifact_id: str = "cv.raw.images",
    source_version: str = "v0",
) -> dict[str, str]:
    manifest = profile.dataset("manifest")
    artifact_ref = materialize_manifest_artifact(
        backend.artifact_store,
        artifact_id=manifest.artifact_id,
        version=version_id,
        entries=entries,
        producer_run_id=run_id,
    )
    _, content = backend.artifact_store.get(artifact_ref.artifact_id, artifact_ref.version)
    quality = backend.quality_evaluator.evaluate(artifact_ref, content)
    dataset_version = register_manifest_dataset(
        backend,
        profile,
        artifact_ref=artifact_ref,
        version_id=version_id,
        quality_report_id=quality.report_id,
    )
    record_manifest_lineage(
        backend,
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


def ingest_manifest_from_entries(
    entries: list[dict[str, Any]],
    *,
    profile: CvopsProfile,
    run_id: str,
    version_id: Optional[str] = None,
    backend_root: Optional[Path] = None,
) -> dict[str, str]:
    resolved_version = version_id or manifest_version_id(entries)
    backend = LocalBackend.create(backend_root)
    try:
        return ingest_manifest(
            backend,
            profile,
            entries,
            version_id=resolved_version,
            run_id=run_id,
        )
    finally:
        backend.close()
