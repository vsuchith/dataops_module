"""LakeFS adapter — wraps LakeFSResource without changing its API."""

from __future__ import annotations

from typing import Any

from src.dataops.domain.artifact import (
    ArtifactKind,
    ArtifactRef,
    ArtifactState,
    Checksum,
    ProviderReplayMetadata,
)
from src.dataops.domain.errors import ArtifactNotFoundError


class LakeFSArtifactStoreAdapter:
    """Delegates object IO to the existing LakeFSResource implementation."""

    def __init__(self, lakefs_resource: Any, *, repo: str, branch: str) -> None:
        self._lakefs = lakefs_resource
        self._repo = repo
        self._branch = branch

    def upload_bytes(self, key: str, content: bytes, *, message: str = "dataops upload") -> str:
        self._lakefs.upload_content(self._repo, self._branch, content, key)
        commit = self._lakefs.commit(self._repo, self._branch, message)
        return str(commit.get("id", "unknown"))

    def download_bytes(self, key: str) -> bytes:
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        try:
            self._lakefs.download_file(self._repo, self._branch, key, tmp_path)
            return Path(tmp_path).read_bytes()
        except Exception as exc:
            raise ArtifactNotFoundError(f"lakefs object {key} not found") from exc
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def list_keys(self, prefix: str = "") -> list[str]:
        return self._lakefs.list_objects(self._repo, self._branch, prefix=prefix)

    def to_artifact_ref(
        self,
        *,
        artifact_id: str,
        version: str,
        key: str,
        checksum: Checksum,
        state: ArtifactState = ArtifactState.PUBLISHED,
    ) -> ArtifactRef:
        commit = self._lakefs.get_commit(self._repo, self._branch)
        return ArtifactRef(
            artifact_id=artifact_id,
            version=version,
            kind=ArtifactKind.GENERIC,
            uri=self._lakefs.get_object_url(self._repo, self._branch, key),
            checksum=checksum,
            state=state,
            provider_replay=ProviderReplayMetadata(
                lakefs_repo=self._repo,
                lakefs_branch=self._branch,
                lakefs_commit=str(commit.get("id", "unknown")),
            ),
        )
