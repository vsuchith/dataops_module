"""Simple offline quality evaluator."""

from __future__ import annotations

from src.dataops.domain.artifact import ArtifactRef, ArtifactState
from src.dataops.domain.quality import QualityCheck, QualityReport, QualitySeverity


class LocalDataQualityEvaluator:
    def evaluate(self, ref: ArtifactRef, content: bytes) -> QualityReport:
        checks: list[QualityCheck] = []

        checks.append(
            QualityCheck(
                name="non_empty_content",
                severity=QualitySeverity.CRITICAL,
                passed=len(content) > 0,
                message="artifact bytes must not be empty",
            )
        )
        checks.append(
            QualityCheck(
                name="published_has_uri",
                severity=QualitySeverity.CRITICAL,
                passed=bool(ref.uri.strip()) if ref.state == ArtifactState.PUBLISHED else True,
                message="published artifacts require uri",
            )
        )
        checks.append(
            QualityCheck(
                name="checksum_declared",
                severity=QualitySeverity.WARNING,
                passed=bool(ref.checksum.value),
                message="checksum should be declared before publish",
            )
        )

        return QualityReport.from_checks(
            report_id=f"qr-{ref.artifact_id}-{ref.version}",
            artifact_id=ref.artifact_id,
            artifact_version=ref.version,
            checks=checks,
            evaluator_run_id="local-lite",
        )
