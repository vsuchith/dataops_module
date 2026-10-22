"""Quality evaluation reports."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class QualitySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class QualityCheck(BaseModel):
    name: str
    severity: QualitySeverity
    passed: bool
    evidence_uri: Optional[str] = None
    message: Optional[str] = None


class QualityReport(BaseModel):
    report_id: str
    artifact_id: str
    artifact_version: str
    checks: list[QualityCheck] = Field(default_factory=list)
    pass_fail: bool = True
    evaluated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    evaluator_run_id: Optional[str] = None

    @field_validator("report_id", "artifact_id", "artifact_version", "evaluated_at")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v

    @classmethod
    def from_checks(
        cls,
        report_id: str,
        artifact_id: str,
        artifact_version: str,
        checks: list[QualityCheck],
        evaluator_run_id: Optional[str] = None,
        evaluated_at: Optional[str] = None,
    ) -> QualityReport:
        failed_critical = any(
            not c.passed and c.severity == QualitySeverity.CRITICAL for c in checks
        )
        return cls(
            report_id=report_id,
            artifact_id=artifact_id,
            artifact_version=artifact_version,
            checks=checks,
            pass_fail=not failed_critical,
            evaluator_run_id=evaluator_run_id,
            evaluated_at=evaluated_at
            or datetime.now(timezone.utc).isoformat(),
        )
