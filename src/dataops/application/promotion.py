"""Promotion orchestration with fail-closed validation (ADR-009, SEC-006)."""

from __future__ import annotations

from src.dataops.domain.artifact import ArtifactState
from src.dataops.domain.errors import ValidationError
from src.dataops.domain.promotion import (
    PromotionAuditEvent,
    PromotionReceipt,
    PromotionRequest,
    PromotionStatus,
)
from src.dataops.ports.artifact_store import ArtifactStore
from src.dataops.ports.promotion_consistency import PromotionConsistencyPort


class PromotionService:
    def __init__(
        self,
        *,
        artifact_store: ArtifactStore,
        consistency: PromotionConsistencyPort,
    ) -> None:
        self._artifacts = artifact_store
        self._consistency = consistency

    def promote(self, request: PromotionRequest) -> PromotionReceipt:
        if not request.authorized_by or not request.authorized_by.strip():
            raise ValidationError("promotion requires authorization (SEC-006)")

        ref = self._artifacts.head(request.artifact_id, request.version)
        if ref.state not in {ArtifactState.VALIDATED, ArtifactState.PUBLISHED}:
            raise ValidationError(
                f"artifact {ref.identity_key()} must be validated before promotion "
                f"(state={ref.state.value})"
            )

        missing = request.target_checkpoint.missing_pins()
        if missing:
            raise ValidationError(
                f"promotion fail-closed: missing consistency pins: {', '.join(missing)}"
            )

        return self._consistency.promote(request)

    def rollback(self, receipt: PromotionReceipt) -> PromotionReceipt:
        if receipt.status != PromotionStatus.COMMITTED:
            raise ValidationError("only committed promotions can be rolled back")
        return self._consistency.rollback(receipt)

    @staticmethod
    def audit_event(
        request: PromotionRequest,
        *,
        event_type: str,
        detail: str,
    ) -> PromotionAuditEvent:
        return PromotionAuditEvent(
            event_type=event_type,
            correlation_id=request.correlation_id,
            run_id=request.run_id,
            artifact_id=request.artifact_id,
            version=request.version,
            detail=detail,
        )
