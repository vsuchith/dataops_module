"""Factory for the local-lite profile (ADR-007)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.dataops.integrations.local.duckdb_store import DuckDBCatalogStore
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore
from src.dataops.integrations.local.quality import LocalDataQualityEvaluator
from src.dataops.ports.artifact_store import ArtifactStore
from src.dataops.ports.dataset_catalog import DatasetCatalog
from src.dataops.ports.lineage_store import LineageStore
from src.dataops.ports.quality_evaluator import DataQualityEvaluator


@dataclass
class LocalBackend:
    artifact_store: ArtifactStore
    dataset_catalog: DatasetCatalog
    lineage_store: LineageStore
    quality_evaluator: DataQualityEvaluator

    @classmethod
    def create(cls, root: Optional[Path] = None) -> LocalBackend:
        base = root or Path(".dataops-local")
        catalog = DuckDBCatalogStore(base / "catalog.duckdb")
        return cls(
            artifact_store=LocalFilesystemArtifactStore(base / "artifacts"),
            dataset_catalog=catalog,
            lineage_store=catalog,
            quality_evaluator=LocalDataQualityEvaluator(),
        )

    def close(self) -> None:
        catalog = self.dataset_catalog
        if isinstance(catalog, DuckDBCatalogStore):
            catalog.close()
