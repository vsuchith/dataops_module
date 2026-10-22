"""Data quality evaluation port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.dataops.domain.artifact import ArtifactRef
from src.dataops.domain.quality import QualityReport


@runtime_checkable
class DataQualityEvaluator(Protocol):
    def evaluate(self, ref: ArtifactRef, content: bytes) -> QualityReport: ...
