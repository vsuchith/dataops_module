"""Lakehouse promotion consistency model (ADR-009)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.dataops.domain.artifact import ProviderReplayMetadata


class PromotionStatus(str, Enum):
    PENDING = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class ConsistencyCheckpoint(BaseModel):
    """Replay pins across LakeFS, Iceberg, and Nessie (ADR-002 metadata)."""

    lakefs_repo: Optional[str] = None
    lakefs_branch: Optional[str] = None
    lakefs_commit: Optional[str] = None
    iceberg_snapshot: Optional[str] = None
    nessie_ref: Optional[str] = None

    @field_validator("lakefs_commit", "iceberg_snapshot", "nessie_ref")
    @classmethod
    def pin_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("consistency pin must not be blank")
        return v

    def as_replay_metadata(self) -> ProviderReplayMetadata:
        return ProviderReplayMetadata(
            lakefs_repo=self.lakefs_repo,
            lakefs_branch=self.lakefs_branch,
            lakefs_commit=self.lakefs_commit,
            iceberg_snapshot=self.iceberg_snapshot,
            nessie_ref=self.nessie_ref,
        )

    def missing_pins(self) -> list[str]:
        missing: list[str] = []
        if not self.lakefs_commit:
            missing.append("lakefs_commit")
        if not self.iceberg_snapshot:
            missing.append("iceberg_snapshot")
        if not self.nessie_ref:
            missing.append("nessie_ref")
        return missing


class PromotionRequest(BaseModel):
    artifact_id: str
    version: str
    run_id: str
    correlation_id: str
    target_checkpoint: ConsistencyCheckpoint
    require_quality_pass: bool = True
    authorized_by: Optional[str] = None

    @field_validator("artifact_id", "version", "run_id", "correlation_id")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v


class PromotionAuditEvent(BaseModel):
  """SEC-007 audit event for promotion lifecycle."""

  event_type: str
  correlation_id: str
  run_id: str
  artifact_id: str
  version: str
  detail: str
  recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PromotionReceipt(BaseModel):
    request: PromotionRequest
    status: PromotionStatus
    committed_checkpoint: Optional[ConsistencyCheckpoint] = None
    previous_checkpoint: Optional[ConsistencyCheckpoint] = None
    audit_events: list[PromotionAuditEvent] = Field(default_factory=list)
    failure_reason: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        return self.status == PromotionStatus.COMMITTED
