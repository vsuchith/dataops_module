"""Annotation dataset versioning for CVOps offline acceptance."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from src.cvops.compatibility.specs import CvopsProfile
from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState
from src.dataops.domain.dataset import DatasetModality, DatasetVersion
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore


def build_annotation_payload(
    manifest_entries: list[dict[str, Any]],
    *,
    class_name: str = "object",
) -> dict[str, Any]:
    annotations: list[dict[str, Any]] = []
    for entry in manifest_entries:
        image_id = entry["image_id"]
        digest = hashlib.sha256(image_id.encode()).hexdigest()
        annotations.append(
            {
                "annotation_id": f"ann-{digest[:12]}",
                "image_id": image_id,
                "class_name": class_name,
                "bbox": [
                    int(digest[0:2], 16) % 80,
                    int(digest[2:4], 16) % 80,
                    80 + int(digest[4:6], 16) % 40,
                    80 + int(digest[6:8], 16) % 40,
                ],
                "confidence": 0.95,
            }
        )
    return {"annotations": annotations, "count": len(annotations)}


def materialize_annotation_artifact(
    store: LocalFilesystemArtifactStore,
    *,
    artifact_id: str,
    version: str,
    payload: dict[str, Any],
    producer_run_id: Optional[str] = None,
) -> ArtifactRef:
    content = json.dumps(payload, sort_keys=True).encode("utf-8")
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id=artifact_id,
        version=version,
        kind=ArtifactKind.ANNOTATION,
        uri=f"file:///{artifact_id}/{version}",
        checksum=checksum,
        state=ArtifactState.VALIDATED,
        media_type="application/json",
        producer_run_id=producer_run_id,
        metadata={"annotation_count": str(payload["count"])},
    )
    return store.put(ref, content)


def ingest_annotations(
    backend: LocalBackend,
    profile: CvopsProfile,
    manifest_entries: list[dict[str, Any]],
    *,
    manifest_artifact_id: str,
    manifest_version: str,
    version_id: str,
    run_id: str,
) -> dict[str, str]:
    payload = build_annotation_payload(manifest_entries)
    artifact_id = "cv.annotations"
    artifact_ref = materialize_annotation_artifact(
        backend.artifact_store,
        artifact_id=artifact_id,
        version=version_id,
        payload=payload,
        producer_run_id=run_id,
    )
    _, content = backend.artifact_store.get(artifact_ref.artifact_id, artifact_ref.version)
    quality = backend.quality_evaluator.evaluate(artifact_ref, content)
    dataset_version = DatasetVersion(
        dataset_id="cv.annotations",
        version_id=version_id,
        modality=DatasetModality.IMAGE_COLLECTION,
        physical_artifact_ids=[artifact_ref.artifact_id],
        schema_or_manifest_ref="schema://cv/annotations/v1",
        quality_report_id=quality.report_id,
    )
    backend.dataset_catalog.register(dataset_version)
    backend.lineage_store.record_edge(
        LineageEdge(
            source_artifact_id=manifest_artifact_id,
            source_version=manifest_version,
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
