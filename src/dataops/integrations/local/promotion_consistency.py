"""Local reference promotion consistency store (ADR-009, ADR-007)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.dataops.application.promotion import PromotionService
from src.dataops.domain.artifact import ArtifactRef, ArtifactState
from src.dataops.domain.errors import ValidationError
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.domain.promotion import (
    ConsistencyCheckpoint,
    PromotionAuditEvent,
    PromotionReceipt,
    PromotionRequest,
    PromotionStatus,
)
from src.dataops.integrations.local.duckdb_store import DuckDBCatalogStore
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore
from src.dataops.ports.artifact_store import ArtifactStore
from src.dataops.ports.lineage_store import LineageStore


@dataclass
class _PromotionSnapshot:
    artifact: ArtifactRef
    checkpoint: Optional[ConsistencyCheckpoint]


class LocalPromotionConsistency:
    """Filesystem-backed promotion transaction boundary for offline CI."""

    def __init__(
        self,
        *,
        artifact_store: ArtifactStore,
        lineage_store: LineageStore,
        root: Path,
    ) -> None:
        self._artifacts = artifact_store
        self._lineage = lineage_store
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._audit_path = self._root / "promotion-audit.jsonl"

    def _append_audit(self, event: PromotionAuditEvent) -> None:
        with self._audit_path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json())
            handle.write("\n")

    def _persist_audit_events(self, events: list[PromotionAuditEvent]) -> None:
        """SEC-007: audit persistence is the final commit phase of the transaction."""
        for event in events:
            self._append_audit(event)

    def _checkpoint_path(self, artifact_id: str, version: str) -> Path:
        return self._root / "checkpoints" / artifact_id / version / "checkpoint.json"

    def _read_checkpoint(self, artifact_id: str, version: str) -> ConsistencyCheckpoint | None:
        path = self._checkpoint_path(artifact_id, version)
        if not path.exists():
            return None
        return ConsistencyCheckpoint.model_validate_json(path.read_text(encoding="utf-8"))

    def _write_checkpoint(
        self,
        artifact_id: str,
        version: str,
        checkpoint: ConsistencyCheckpoint,
    ) -> None:
        path = self._checkpoint_path(artifact_id, version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(checkpoint.model_dump_json(indent=2), encoding="utf-8")

    def _delete_checkpoint(self, artifact_id: str, version: str) -> None:
        path = self._checkpoint_path(artifact_id, version)
        if path.exists():
            path.unlink()

    def _snapshot(self, artifact_id: str, version: str) -> _PromotionSnapshot:
        return _PromotionSnapshot(
            artifact=self._artifacts.head(artifact_id, version),
            checkpoint=self._read_checkpoint(artifact_id, version),
        )

    def _commit_artifact_replay(
        self,
        artifact_id: str,
        version: str,
        checkpoint: ConsistencyCheckpoint,
        *,
        target_state: ArtifactState,
    ) -> ArtifactRef:
        ref = self._artifacts.head(artifact_id, version)
        updated = ref.model_copy(
            update={
                "state": target_state,
                "provider_replay": checkpoint.as_replay_metadata(),
            }
        )
        if not isinstance(self._artifacts, LocalFilesystemArtifactStore):
            raise ValidationError("local promotion requires LocalFilesystemArtifactStore")
        return self._artifacts.commit_lifecycle(updated)

    def _restore_snapshot(self, snapshot: _PromotionSnapshot) -> None:
        if not isinstance(self._artifacts, LocalFilesystemArtifactStore):
            raise ValidationError("local promotion requires LocalFilesystemArtifactStore")
        self._artifacts.commit_lifecycle(snapshot.artifact)
        if snapshot.checkpoint is None:
            self._delete_checkpoint(snapshot.artifact.artifact_id, snapshot.artifact.version)
        else:
            self._write_checkpoint(
                snapshot.artifact.artifact_id,
                snapshot.artifact.version,
                snapshot.checkpoint,
            )

    def _compensate(
        self,
        snapshot: _PromotionSnapshot,
        lineage_edge: LineageEdge | None,
    ) -> None:
        if lineage_edge is not None and isinstance(self._lineage, DuckDBCatalogStore):
            self._lineage.delete_edge(lineage_edge)
        self._restore_snapshot(snapshot)

    def _execute_promotion_transaction(
        self,
        request: PromotionRequest,
        *,
        snapshot: _PromotionSnapshot,
        lineage_edge: LineageEdge,
        events: list[PromotionAuditEvent],
        previous: Optional[ConsistencyCheckpoint],
    ) -> PromotionReceipt:
        """Lineage → checkpoint → publish → audit (compensate on any failure)."""
        try:
            self._lineage.record_edge(lineage_edge)
            self._write_checkpoint(
                request.artifact_id,
                request.version,
                request.target_checkpoint,
            )
            self._commit_artifact_replay(
                request.artifact_id,
                request.version,
                request.target_checkpoint,
                target_state=ArtifactState.PUBLISHED,
            )
            events.append(
                PromotionService.audit_event(
                    request,
                    event_type="promotion_committed",
                    detail="lakehouse consistency pins committed",
                )
            )
            receipt = PromotionReceipt(
                request=request,
                status=PromotionStatus.COMMITTED,
                committed_checkpoint=request.target_checkpoint,
                previous_checkpoint=previous,
                audit_events=list(events),
            )
            self._persist_audit_events(events)
            return receipt
        except Exception:
            self._compensate(snapshot, lineage_edge)
            raise

    def promote(self, request: PromotionRequest) -> PromotionReceipt:
        events: list[PromotionAuditEvent] = [
            PromotionService.audit_event(
                request,
                event_type="promotion_requested",
                detail="local promotion transaction started",
            )
        ]
        previous = self._read_checkpoint(request.artifact_id, request.version)

        try:
            ref = self._artifacts.head(request.artifact_id, request.version)
            if ref.state == ArtifactState.PUBLISHED and previous == request.target_checkpoint:
                events.append(
                    PromotionService.audit_event(
                        request,
                        event_type="promotion_idempotent",
                        detail="artifact already published at target checkpoint",
                    )
                )
                receipt = PromotionReceipt(
                    request=request,
                    status=PromotionStatus.COMMITTED,
                    committed_checkpoint=request.target_checkpoint,
                    previous_checkpoint=previous,
                    audit_events=events,
                )
                self._persist_audit_events(events)
                return receipt

            snapshot = self._snapshot(request.artifact_id, request.version)
            lineage_edge = LineageEdge(
                source_artifact_id=request.artifact_id,
                source_version=request.version,
                target_artifact_id=request.artifact_id,
                target_version=request.version,
                operation=LineageOperation.PROMOTE,
                run_id=request.run_id,
                metadata={"correlation_id": request.correlation_id},
            )
            return self._execute_promotion_transaction(
                request,
                snapshot=snapshot,
                lineage_edge=lineage_edge,
                events=events,
                previous=previous,
            )
        except Exception as exc:
            events.append(
                PromotionService.audit_event(
                    request,
                    event_type="promotion_failed",
                    detail=str(exc),
                )
            )
            receipt = PromotionReceipt(
                request=request,
                status=PromotionStatus.FAILED,
                previous_checkpoint=previous,
                audit_events=events,
                failure_reason=str(exc),
            )
            try:
                self._persist_audit_events(events)
            except Exception:
                pass
            return receipt

    def rollback(self, receipt: PromotionReceipt) -> PromotionReceipt:
        request = receipt.request
        events = list(receipt.audit_events)
        if receipt.previous_checkpoint is None:
            raise ValidationError("no previous checkpoint to restore")

        snapshot = self._snapshot(request.artifact_id, request.version)
        try:
            self._commit_artifact_replay(
                request.artifact_id,
                request.version,
                receipt.previous_checkpoint,
                target_state=ArtifactState.VALIDATED,
            )
            self._write_checkpoint(
                request.artifact_id,
                request.version,
                receipt.previous_checkpoint,
            )
            events.append(
                PromotionService.audit_event(
                    request,
                    event_type="promotion_rolled_back",
                    detail="restored previous consistency checkpoint",
                )
            )
            rolled = PromotionReceipt(
                request=request,
                status=PromotionStatus.ROLLED_BACK,
                committed_checkpoint=receipt.previous_checkpoint,
                previous_checkpoint=receipt.committed_checkpoint,
                audit_events=events,
            )
            self._persist_audit_events(events[len(receipt.audit_events) :])
            return rolled
        except Exception:
            self._restore_snapshot(snapshot)
            raise

    def read_audit_events(self) -> list[PromotionAuditEvent]:
        if not self._audit_path.exists():
            return []
        events: list[PromotionAuditEvent] = []
        for line in self._audit_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(PromotionAuditEvent.model_validate(json.loads(line)))
        return events
