"""MinIO adapter — wraps MinIOResource without changing its API."""

from __future__ import annotations

from typing import Any


class MinIOObjectStoreAdapter:
    def __init__(self, minio_resource: Any) -> None:
        self._minio = minio_resource

    def upload_file(self, bucket: str, key: str, file_path: str) -> None:
        self._minio.upload_file(bucket, key, file_path)

    def download_file(self, bucket: str, key: str, file_path: str) -> None:
        self._minio.download_file(bucket, key, file_path)

    def list_objects(self, bucket: str, prefix: str = "") -> list[str]:
        return self._minio.list_objects(bucket, prefix=prefix)

    def put_json(self, bucket: str, key: str, data: dict) -> None:
        self._minio.put_json(bucket, key, data)
