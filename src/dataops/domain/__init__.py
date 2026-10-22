"""DataOps kernel — domain-neutral artifact, lineage, and quality types."""

from src.dataops.domain.artifact import (
    ArtifactKind,
    ArtifactRef,
    ArtifactState,
    Checksum,
    ProviderReplayMetadata,
)
from src.dataops.domain.dataset import DatasetModality, DatasetVersion
from src.dataops.domain.errors import (
    ArtifactNotFoundError,
    ChecksumMismatchError,
    DataOpsError,
    ImmutableVersionError,
    ValidationError,
)
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.domain.promotion import (
    ConsistencyCheckpoint,
    PromotionAuditEvent,
    PromotionReceipt,
    PromotionRequest,
    PromotionStatus,
)
from src.dataops.domain.quality import QualityCheck, QualityReport, QualitySeverity

__all__ = [
    "ArtifactKind",
    "ArtifactRef",
    "ArtifactState",
    "Checksum",
    "ProviderReplayMetadata",
    "DatasetModality",
    "DatasetVersion",
    "ArtifactNotFoundError",
    "ChecksumMismatchError",
    "DataOpsError",
    "ValidationError",
    "LineageEdge",
    "LineageOperation",
    "ConsistencyCheckpoint",
    "PromotionAuditEvent",
    "PromotionReceipt",
    "PromotionRequest",
    "PromotionStatus",
    "QualityCheck",
    "QualityReport",
    "QualitySeverity",
]
