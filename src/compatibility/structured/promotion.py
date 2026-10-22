"""Structured promotion helpers (ADR-009)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.dataops.application.promotion import PromotionService
from src.dataops.domain.promotion import ConsistencyCheckpoint, PromotionReceipt, PromotionRequest
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.promotion_consistency import LocalPromotionConsistency


def default_structured_checkpoint(
    *,
    lakefs_commit: str = "lakefs-structured-smoke",
    iceberg_snapshot: str = "snap-structured-smoke",
    nessie_ref: str = "nessie-structured-smoke",
) -> ConsistencyCheckpoint:
    return ConsistencyCheckpoint(
        lakefs_repo="warehouse",
        lakefs_branch="main",
        lakefs_commit=lakefs_commit,
        iceberg_snapshot=iceberg_snapshot,
        nessie_ref=nessie_ref,
    )


def build_promotion_service(
    backend: LocalBackend,
    promotion_root: Path,
) -> PromotionService:
    consistency = LocalPromotionConsistency(
        artifact_store=backend.artifact_store,
        lineage_store=backend.lineage_store,
        root=promotion_root,
    )
    return PromotionService(
        artifact_store=backend.artifact_store,
        consistency=consistency,
    )


def promote_structured_artifact(
    backend: LocalBackend,
    *,
    artifact_id: str,
    version: str,
    run_id: str,
    correlation_id: str,
    promotion_root: Path,
    authorized_by: str = "structured-profile-smoke",
    checkpoint: Optional[ConsistencyCheckpoint] = None,
) -> PromotionReceipt:
    service = build_promotion_service(backend, promotion_root)
    request = PromotionRequest(
        artifact_id=artifact_id,
        version=version,
        run_id=run_id,
        correlation_id=correlation_id,
        target_checkpoint=checkpoint or default_structured_checkpoint(),
        authorized_by=authorized_by,
    )
    return service.promote(request)
