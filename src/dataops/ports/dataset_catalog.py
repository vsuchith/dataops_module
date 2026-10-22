"""Dataset catalog port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.dataops.domain.dataset import DatasetVersion


@runtime_checkable
class DatasetCatalog(Protocol):
    def register(self, version: DatasetVersion) -> DatasetVersion: ...

    def get(self, dataset_id: str, version_id: str) -> DatasetVersion: ...
