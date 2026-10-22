"""ADR-009 promotion consistency — local reference backend tests."""

import json

import pytest

from src.dataops.application.promotion import PromotionService
from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState
from src.dataops.domain.errors import ImmutableMetadataError, ValidationError
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.domain.promotion import ConsistencyCheckpoint, PromotionRequest, PromotionStatus
from src.dataops.integrations.enterprise.lakehouse_promotion import (
    EnterpriseLakehousePromotionConsistency,
    build_enterprise_promotion_service,
)
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore
from src.dataops.integrations.local.promotion_consistency import LocalPromotionConsistency


def _checkpoint(commit: str = "lakefs-abc") -> ConsistencyCheckpoint:
    return ConsistencyCheckpoint(
        lakefs_repo="bronze",
        lakefs_branch="main",
        lakefs_commit=commit,
        iceberg_snapshot="snap-001",
        nessie_ref="nessie-main",
    )


def _validated_artifact(
    artifact_id: str = "dataset.bronze",
    version: str = "v1",
    *,
    content: bytes = b"table-bytes",
) -> tuple[ArtifactRef, bytes]:
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id=artifact_id,
        version=version,
        kind=ArtifactKind.STRUCTURED_TABLE,
        uri=f"file:///{artifact_id}/{version}",
        checksum=checksum,
        state=ArtifactState.VALIDATED,
    )
    return ref, content


@pytest.fixture
def promotion_stack(tmp_path):
    backend = LocalBackend.create(tmp_path)
    consistency = LocalPromotionConsistency(
        artifact_store=backend.artifact_store,
        lineage_store=backend.lineage_store,
        root=tmp_path / "promotion",
    )
    service = PromotionService(
        artifact_store=backend.artifact_store,
        consistency=consistency,
    )
    yield backend, consistency, service
    backend.close()


def test_promote_commits_checkpoint_and_audit_event(promotion_stack) -> None:
    backend, consistency, service = promotion_stack
    ref, content = _validated_artifact()
    backend.artifact_store.put(ref, content)

    request = PromotionRequest(
        artifact_id=ref.artifact_id,
        version=ref.version,
        run_id="run-promote-001",
        correlation_id="corr-001",
        target_checkpoint=_checkpoint(),
        authorized_by="ci-operator",
    )
    receipt = service.promote(request)

    assert receipt.succeeded
    assert receipt.status == PromotionStatus.COMMITTED
    assert receipt.committed_checkpoint == request.target_checkpoint

    published, _ = backend.artifact_store.get(ref.artifact_id, ref.version)
    assert published.state == ArtifactState.PUBLISHED
    assert published.provider_replay.lakefs_commit == "lakefs-abc"

    edges = backend.lineage_store.list_upstream(ref.artifact_id, ref.version)
    assert len(edges) == 1
    assert edges[0].operation == LineageOperation.PROMOTE
    assert edges[0].run_id == "run-promote-001"

    audit = consistency.read_audit_events()
    assert any(event.event_type == "promotion_committed" for event in audit)


def test_promote_fail_closed_on_missing_pins(promotion_stack) -> None:
    backend, _, service = promotion_stack
    ref, content = _validated_artifact(artifact_id="dataset.silver", content=b"silver")
    backend.artifact_store.put(ref, content)

    request = PromotionRequest(
        artifact_id=ref.artifact_id,
        version=ref.version,
        run_id="run-promote-002",
        correlation_id="corr-002",
        target_checkpoint=ConsistencyCheckpoint(lakefs_commit="only-lakefs"),
        authorized_by="ci-operator",
    )
    with pytest.raises(ValidationError, match="missing consistency pins"):
        service.promote(request)


def test_promote_requires_authorization_always(promotion_stack) -> None:
    _, _, service = promotion_stack
    request = PromotionRequest(
        artifact_id="dataset.gold",
        version="v1",
        run_id="run-promote-003",
        correlation_id="corr-003",
        target_checkpoint=_checkpoint(),
        require_quality_pass=False,
    )
    with pytest.raises(ValidationError, match="authorization"):
        service.promote(request)


def test_put_cannot_rewrite_lifecycle_metadata(promotion_stack) -> None:
    backend, _, _ = promotion_stack
    ref, content = _validated_artifact(artifact_id="dataset.immutable", content=b"immutable")
    backend.artifact_store.put(ref, content)
    tampered = ref.model_copy(update={"state": ArtifactState.PUBLISHED})
    with pytest.raises(ImmutableMetadataError):
        backend.artifact_store.put(tampered, content)


class _FailingLineageStore:
    def __init__(self, inner) -> None:
        self._inner = inner
        self.fail_next = False

    def record_edge(self, edge: LineageEdge) -> LineageEdge:
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("injected lineage failure")
        return self._inner.record_edge(edge)

    def list_upstream(self, artifact_id: str, version: str):
        return self._inner.list_upstream(artifact_id, version)

    def list_downstream(self, artifact_id: str, version: str):
        return self._inner.list_downstream(artifact_id, version)

    def delete_edge(self, edge: LineageEdge) -> None:
        return self._inner.delete_edge(edge)


def test_promote_lineage_failure_leaves_no_partial_state(tmp_path) -> None:
    backend = LocalBackend.create(tmp_path)
    failing_lineage = _FailingLineageStore(backend.lineage_store)
    consistency = LocalPromotionConsistency(
        artifact_store=backend.artifact_store,
        lineage_store=failing_lineage,
        root=tmp_path / "promotion",
    )
    service = PromotionService(
        artifact_store=backend.artifact_store,
        consistency=consistency,
    )
    ref, content = _validated_artifact(artifact_id="dataset.partial", content=b"partial")
    backend.artifact_store.put(ref, content)
    prior = backend.artifact_store.head(ref.artifact_id, ref.version)

    failing_lineage.fail_next = True
    receipt = service.promote(
        PromotionRequest(
            artifact_id=ref.artifact_id,
            version=ref.version,
            run_id="run-promote-fail",
            correlation_id="corr-fail",
            target_checkpoint=_checkpoint("lakefs-fail"),
            authorized_by="ci-operator",
        )
    )

    assert receipt.status == PromotionStatus.FAILED
    restored = backend.artifact_store.head(ref.artifact_id, ref.version)
    assert restored.state == prior.state
    assert restored.provider_replay == prior.provider_replay
    checkpoint_path = tmp_path / "promotion" / "checkpoints" / ref.artifact_id / ref.version
    assert not (checkpoint_path / "checkpoint.json").exists()
    upstream = backend.lineage_store.list_upstream(ref.artifact_id, ref.version)
    assert not any(edge.operation == LineageOperation.PROMOTE for edge in upstream)
    backend.close()


def test_promote_audit_failure_leaves_no_partial_state(tmp_path) -> None:
    backend = LocalBackend.create(tmp_path)
    consistency = LocalPromotionConsistency(
        artifact_store=backend.artifact_store,
        lineage_store=backend.lineage_store,
        root=tmp_path / "promotion",
    )
    original_persist = consistency._persist_audit_events

    def failing_persist(events: list) -> None:
        if any(event.event_type == "promotion_committed" for event in events):
            raise RuntimeError("injected audit failure")
        original_persist(events)

    consistency._persist_audit_events = failing_persist  # type: ignore[method-assign]
    service = PromotionService(
        artifact_store=backend.artifact_store,
        consistency=consistency,
    )
    ref, content = _validated_artifact(artifact_id="dataset.audit-fail", content=b"audit-fail")
    backend.artifact_store.put(ref, content)
    prior = backend.artifact_store.head(ref.artifact_id, ref.version)

    receipt = service.promote(
        PromotionRequest(
            artifact_id=ref.artifact_id,
            version=ref.version,
            run_id="run-promote-audit-fail",
            correlation_id="corr-audit-fail",
            target_checkpoint=_checkpoint("lakefs-audit-fail"),
            authorized_by="ci-operator",
        )
    )

    assert receipt.status == PromotionStatus.FAILED
    restored = backend.artifact_store.head(ref.artifact_id, ref.version)
    assert restored.state == prior.state
    assert restored.provider_replay == prior.provider_replay
    checkpoint_path = tmp_path / "promotion" / "checkpoints" / ref.artifact_id / ref.version
    assert not (checkpoint_path / "checkpoint.json").exists()
    upstream = backend.lineage_store.list_upstream(ref.artifact_id, ref.version)
    assert not any(edge.operation == LineageOperation.PROMOTE for edge in upstream)
    backend.close()


def test_enterprise_promotion_validates_full_pin_set(tmp_path) -> None:
    backend = LocalBackend.create(tmp_path)
    service = build_enterprise_promotion_service(
        artifact_store=backend.artifact_store,
        lineage_store=backend.lineage_store,
        root=tmp_path / "enterprise-promotion",
    )
    ref, content = _validated_artifact(artifact_id="dataset.enterprise", content=b"enterprise")
    backend.artifact_store.put(ref, content)

    with pytest.raises(ValidationError, match="lakefs_repo"):
        service.promote(
            PromotionRequest(
                artifact_id=ref.artifact_id,
                version=ref.version,
                run_id="run-enterprise-fail",
                correlation_id="corr-enterprise-fail",
                target_checkpoint=ConsistencyCheckpoint(
                    lakefs_commit="only-commit",
                    iceberg_snapshot="snap-1",
                    nessie_ref="nessie-1",
                ),
                authorized_by="ci-operator",
            )
        )

    receipt = service.promote(
        PromotionRequest(
            artifact_id=ref.artifact_id,
            version=ref.version,
            run_id="run-enterprise-ok",
            correlation_id="corr-enterprise-ok",
            target_checkpoint=ConsistencyCheckpoint(
                lakefs_repo="warehouse",
                lakefs_branch="main",
                lakefs_commit="lakefs-enterprise",
                iceberg_snapshot="snap-enterprise",
                nessie_ref="nessie-enterprise",
            ),
            authorized_by="ci-operator",
        )
    )
    assert receipt.succeeded
    backend.close()


def test_rollback_restores_previous_checkpoint(promotion_stack) -> None:
    backend, consistency, service = promotion_stack
    ref, content = _validated_artifact(artifact_id="dataset.gold", content=b"gold")
    backend.artifact_store.put(ref, content)

    first = service.promote(
        PromotionRequest(
            artifact_id=ref.artifact_id,
            version=ref.version,
            run_id="run-promote-004",
            correlation_id="corr-004",
            target_checkpoint=_checkpoint("lakefs-v1"),
            authorized_by="ci-operator",
        )
    )
    second = service.promote(
        PromotionRequest(
            artifact_id=ref.artifact_id,
            version=ref.version,
            run_id="run-promote-005",
            correlation_id="corr-005",
            target_checkpoint=_checkpoint("lakefs-v2"),
            authorized_by="ci-operator",
        )
    )
    rolled = service.rollback(second)

    assert rolled.status == PromotionStatus.ROLLED_BACK
    restored, _ = backend.artifact_store.get(ref.artifact_id, ref.version)
    assert restored.state == ArtifactState.VALIDATED
    assert restored.provider_replay.lakefs_commit == "lakefs-v1"

    audit = consistency.read_audit_events()
    assert any(event.event_type == "promotion_rolled_back" for event in audit)
    assert first.committed_checkpoint is not None
