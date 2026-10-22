"""Local reference backend (ADR-007)."""

from src.dataops.integrations.local.backend import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore
from src.dataops.integrations.local.duckdb_store import DuckDBCatalogStore
from src.dataops.integrations.local.promotion_consistency import LocalPromotionConsistency
from src.dataops.integrations.local.quality import LocalDataQualityEvaluator

__all__ = [
    "LocalBackend",
    "LocalFilesystemArtifactStore",
    "DuckDBCatalogStore",
    "LocalDataQualityEvaluator",
    "LocalPromotionConsistency",
]
