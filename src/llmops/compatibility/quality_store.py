"""Persist QualityReport records via kernel artifact store (E4)."""

from __future__ import annotations

import hashlib
import json

from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState
from src.dataops.domain.errors import ArtifactNotFoundError
from src.dataops.domain.quality import QualityReport
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore


def _report_semantic_key(report: QualityReport) -> str:
    payload = report.model_dump()
    payload.pop("evaluated_at", None)
    return json.dumps(payload, sort_keys=True)


def _deterministic_evaluated_at(report: QualityReport) -> str:
    """RFC3339 canonical observation time (content-derived, not wall-clock).

    The timestamp is stable for idempotent re-runs with identical report semantics.
    Wall-clock evaluation time is not persisted here; see E5 hardening if needed.
    """
    digest = hashlib.sha256(_report_semantic_key(report).encode("utf-8")).hexdigest()
    seconds = int(digest[0:8], 16) % 60
    micros = int(digest[8:16], 16) % 1_000_000
    return f"1970-01-01T00:00:{seconds:02d}.{micros:06d}Z"


def persist_quality_report(backend: LocalBackend, report: QualityReport) -> ArtifactRef:
    """Store a quality report as a kernel artifact (idempotent for identical evaluations)."""
    store = backend.artifact_store
    try:
        _, content = store.get(report.report_id, report.artifact_version)
        existing = QualityReport.model_validate_json(content.decode("utf-8"))
        if _report_semantic_key(existing) == _report_semantic_key(report):
            return store.head(report.report_id, report.artifact_version)
    except ArtifactNotFoundError:
        pass

    canonical = report.model_copy(update={"evaluated_at": _deterministic_evaluated_at(report)})
    content = canonical.model_dump_json().encode("utf-8")
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id=canonical.report_id,
        version=canonical.artifact_version,
        kind=ArtifactKind.GENERIC,
        uri=f"file:///{canonical.report_id}/{canonical.artifact_version}",
        checksum=checksum,
        state=ArtifactState.VALIDATED,
        media_type="application/json",
        producer_run_id=canonical.evaluator_run_id,
        metadata={"pass_fail": str(canonical.pass_fail).lower()},
    )
    return store.put(ref, content)


def load_quality_report(
    backend: LocalBackend,
    report_id: str,
    artifact_version: str,
) -> QualityReport:
    _, content = backend.artifact_store.get(report_id, artifact_version)
    return QualityReport.model_validate_json(content.decode("utf-8"))
