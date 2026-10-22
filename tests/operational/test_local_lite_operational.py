"""Operational acceptance: local-lite profile (ADR-007)."""

from pathlib import Path

from src.compatibility.structured.promotion import build_promotion_service, default_structured_checkpoint
from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState, Checksum
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.domain.promotion import PromotionRequest, PromotionStatus
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore


def test_local_lite_artifact_lifecycle(tmp_path: Path) -> None:
    backend = LocalBackend.create(tmp_path)
    try:
        content = b"payload"
        checksum = LocalFilesystemArtifactStore.checksum(content)
        ref = ArtifactRef(
            artifact_id="demo.artifact",
            version="v1",
            kind=ArtifactKind.GENERIC,
            uri="file:///demo/v1",
            checksum=checksum,
            state=ArtifactState.DRAFT,
        )
        stored = backend.artifact_store.put(ref, content)
        assert stored.checksum.value

        _, content_bytes = backend.artifact_store.get(stored.artifact_id, stored.version)
        quality = backend.quality_evaluator.evaluate(stored, content_bytes)
        assert quality.pass_fail is True

        validated = stored.model_copy(update={"state": ArtifactState.VALIDATED})
        backend.artifact_store.commit_lifecycle(validated)

        backend.lineage_store.record_edge(
            LineageEdge(
                source_artifact_id="source.demo",
                source_version="v0",
                target_artifact_id=ref.artifact_id,
                target_version=ref.version,
                operation=LineageOperation.INGEST,
                run_id="run-local-lite",
            )
        )
        upstream = backend.lineage_store.list_upstream(ref.artifact_id, ref.version)
        assert upstream[0].run_id == "run-local-lite"

        service = build_promotion_service(backend, tmp_path / "promotion")
        receipt = service.promote(
            PromotionRequest(
                artifact_id=ref.artifact_id,
                version=ref.version,
                run_id="run-local-lite-promote",
                correlation_id="corr-local-lite",
                target_checkpoint=default_structured_checkpoint(
                    lakefs_commit="lakefs-local-lite",
                    iceberg_snapshot="snap-local-lite",
                    nessie_ref="nessie-local-lite",
                ),
                authorized_by="local-lite-smoke",
            )
        )
        assert receipt.status == PromotionStatus.COMMITTED
        published = backend.artifact_store.head(ref.artifact_id, ref.version)
        assert published.state == ArtifactState.PUBLISHED
    finally:
        backend.close()
