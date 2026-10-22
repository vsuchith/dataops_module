"""DataOps kernel — domain-neutral artifact, lineage, and quality platform."""

from src.dataops.domain import (
    ArtifactKind,
    ArtifactRef,
    ArtifactState,
    Checksum,
    DatasetModality,
    DatasetVersion,
    LineageEdge,
    LineageOperation,
    QualityCheck,
    QualityReport,
    QualitySeverity,
)
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.providers import (
    LakeFSArtifactStoreAdapter,
    MinIOObjectStoreAdapter,
    TrinoQueryAdapter,
)
from src.dataops.ports import (
    ArtifactStore,
    DataQualityEvaluator,
    DatasetCatalog,
    LineageStore,
)

__all__ = [
    "ArtifactKind",
    "ArtifactRef",
    "ArtifactState",
    "Checksum",
    "DatasetModality",
    "DatasetVersion",
    "LineageEdge",
    "LineageOperation",
    "QualityCheck",
    "QualityReport",
    "QualitySeverity",
    "ArtifactStore",
    "DatasetCatalog",
    "LineageStore",
    "DataQualityEvaluator",
    "LocalBackend",
    "LakeFSArtifactStoreAdapter",
    "MinIOObjectStoreAdapter",
    "TrinoQueryAdapter",
]
