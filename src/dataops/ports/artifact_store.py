"""Artifact persistence port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.dataops.domain.artifact import ArtifactRef


@runtime_checkable
class ArtifactStore(Protocol):
    def put(self, ref: ArtifactRef, content: bytes) -> ArtifactRef: ...

    def get(self, artifact_id: str, version: str) -> tuple[ArtifactRef, bytes]: ...

    def head(self, artifact_id: str, version: str) -> ArtifactRef: ...

    def list_versions(self, artifact_id: str) -> list[str]: ...
