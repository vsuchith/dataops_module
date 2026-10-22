"""Provider adapters delegating to existing core resources."""

from src.dataops.integrations.providers.lakefs_adapter import LakeFSArtifactStoreAdapter
from src.dataops.integrations.providers.minio_adapter import MinIOObjectStoreAdapter
from src.dataops.integrations.providers.trino_adapter import TrinoQueryAdapter

__all__ = [
    "LakeFSArtifactStoreAdapter",
    "MinIOObjectStoreAdapter",
    "TrinoQueryAdapter",
]
