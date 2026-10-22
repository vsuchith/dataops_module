"""Deterministic CVOps model stub for offline CI acceptance."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore


def run_deterministic_detection_stub(
    manifest_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return stable pseudo-detections derived from manifest image ids."""
    detections: list[dict[str, Any]] = []
    for entry in manifest_entries:
        image_id = entry["image_id"]
        digest = hashlib.sha256(image_id.encode()).hexdigest()
        detections.append(
            {
                "image_id": image_id,
                "class_name": "object",
                "confidence": round(0.5 + (int(digest[:4], 16) % 500) / 1000.0, 3),
                "bbox": [
                    int(digest[0:2], 16) % 50,
                    int(digest[2:4], 16) % 50,
                    100,
                    100,
                ],
            }
        )
    return detections


def materialize_detection_stub_artifact(
    backend: LocalBackend,
    *,
    manifest_artifact_id: str,
    manifest_version: str,
    manifest_entries: list[dict[str, Any]],
    version_id: str,
    run_id: str,
) -> dict[str, Any]:
    detections = run_deterministic_detection_stub(manifest_entries)
    content = json.dumps({"detections": detections}, sort_keys=True).encode("utf-8")
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id="cv.detection_stub",
        version=version_id,
        kind=ArtifactKind.MODEL,
        uri=f"file:///cv/detection_stub/{version_id}",
        checksum=checksum,
        state=ArtifactState.VALIDATED,
        media_type="application/json",
        producer_run_id=run_id,
        metadata={"detection_count": str(len(detections))},
    )
    stored = backend.artifact_store.put(ref, content)
    backend.lineage_store.record_edge(
        LineageEdge(
            source_artifact_id=manifest_artifact_id,
            source_version=manifest_version,
            target_artifact_id=stored.artifact_id,
            target_version=stored.version,
            operation=LineageOperation.TRAIN,
            run_id=run_id,
            metadata={"stub": "deterministic"},
        )
    )
    return {
        "kernel_artifact_id": stored.artifact_id,
        "kernel_artifact_version": stored.version,
        "detections": detections,
    }
