"""Enterprise lakehouse promotion consistency (ADR-009 supplement)."""

from __future__ import annotations

from pathlib import Path

from src.dataops.application.promotion import PromotionService
from src.dataops.domain.errors import ValidationError
from src.dataops.domain.promotion import ConsistencyCheckpoint, PromotionReceipt, PromotionRequest
from src.dataops.integrations.local.promotion_consistency import LocalPromotionConsistency
from src.dataops.ports.artifact_store import ArtifactStore
from src.dataops.ports.lineage_store import LineageStore
from src.dataops.ports.promotion_consistency import PromotionConsistencyPort


class EnterpriseLakehousePromotionConsistency:
    """Enterprise profile adapter delegating to the local transaction boundary.

    Validates full lakehouse pin set before executing the same compensating
    transaction used in offline CI. Production LakeFS/Iceberg/Nessie coordination
    plugs in behind this port without changing PromotionService semantics.
    """

    def __init__(
        self,
        *,
        artifact_store: ArtifactStore,
        lineage_store: LineageStore,
        root: Path,
    ) -> None:
        self._delegate = LocalPromotionConsistency(
            artifact_store=artifact_store,
            lineage_store=lineage_store,
            root=root,
        )

    @staticmethod
    def validate_enterprise_checkpoint(checkpoint: ConsistencyCheckpoint) -> None:
        missing = checkpoint.missing_pins()
        if not checkpoint.lakefs_repo:
            missing.append("lakefs_repo")
        if not checkpoint.lakefs_branch:
            missing.append("lakefs_branch")
        if missing:
            raise ValidationError(
                f"enterprise promotion fail-closed: missing pins: {', '.join(missing)}"
            )

    def promote(self, request: PromotionRequest) -> PromotionReceipt:
        self.validate_enterprise_checkpoint(request.target_checkpoint)
        return self._delegate.promote(request)

    def rollback(self, receipt: PromotionReceipt) -> PromotionReceipt:
        return self._delegate.rollback(receipt)


def build_enterprise_promotion_service(
    *,
    artifact_store: ArtifactStore,
    lineage_store: LineageStore,
    root: Path,
) -> PromotionService:
    consistency: PromotionConsistencyPort = EnterpriseLakehousePromotionConsistency(
        artifact_store=artifact_store,
        lineage_store=lineage_store,
        root=root,
    )
    return PromotionService(artifact_store=artifact_store, consistency=consistency)
