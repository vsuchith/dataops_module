"""Filesystem-backed artifact store for offline CI."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.dataops.domain.artifact import ArtifactRef, ArtifactState, Checksum
from src.dataops.domain.errors import (
    ArtifactNotFoundError,
    ChecksumMismatchError,
    ImmutableMetadataError,
    ImmutableVersionError,
)

_PROTECTED_FIELDS = (
    "state",
    "uri",
    "security_labels",
    "tenant_scope",
    "provider_replay",
)


class LocalFilesystemArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _version_dir(self, artifact_id: str, version: str) -> Path:
        return self._root / artifact_id / version

    @staticmethod
    def checksum(content: bytes) -> Checksum:
        digest = hashlib.sha256(content).hexdigest()
        return Checksum(algorithm="sha256", value=digest)

    def put(self, ref: ArtifactRef, content: bytes) -> ArtifactRef:
        actual = self.checksum(content)
        if ref.checksum.value and ref.checksum.value != actual.value:
            raise ChecksumMismatchError(
                f"declared checksum {ref.checksum.value} does not match content {actual.value}"
            )
        stored_ref = ref.model_copy(update={"checksum": actual})
        version_dir = self._version_dir(ref.artifact_id, ref.version)
        manifest = version_dir / "manifest.json"
        content_path = version_dir / "content.bin"

        if manifest.exists():
            existing_ref = self.head(ref.artifact_id, ref.version)
            existing_content = content_path.read_bytes()
            if self.checksum(existing_content).value == actual.value:
                if existing_ref.model_dump() != stored_ref.model_dump():
                    raise ImmutableMetadataError(
                        f"immutable version {ref.artifact_id}@{ref.version}: "
                        "use commit_lifecycle() for state or replay metadata updates"
                    )
                return existing_ref
            raise ImmutableVersionError(
                f"cannot overwrite immutable version {ref.artifact_id}@{ref.version}"
            )

        version_dir.mkdir(parents=True, exist_ok=True)
        content_path.write_bytes(content)
        manifest.write_text(
            stored_ref.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return stored_ref

    def commit_lifecycle(self, ref: ArtifactRef) -> ArtifactRef:
        """Update lifecycle/replay metadata without changing stored bytes (ADR-009)."""
        manifest = self._version_dir(ref.artifact_id, ref.version) / "manifest.json"
        if not manifest.exists():
            raise ArtifactNotFoundError(f"{ref.artifact_id}@{ref.version} not found")

        existing = self.head(ref.artifact_id, ref.version)
        content_path = self._version_dir(ref.artifact_id, ref.version) / "content.bin"
        actual = self.checksum(content_path.read_bytes())
        if actual.value != ref.checksum.value:
            raise ChecksumMismatchError(
                f"checksum mismatch for lifecycle commit on {ref.identity_key()}"
            )

        for field in ("uri", "security_labels", "tenant_scope"):
            if getattr(existing, field) != getattr(ref, field):
                raise ImmutableMetadataError(
                    f"field {field} is immutable outside initial publish for "
                    f"{ref.identity_key()}"
                )

        if existing.state != ref.state:
            if (
                existing.state == ArtifactState.PUBLISHED
                and ref.state == ArtifactState.VALIDATED
            ):
                pass
            else:
                probe = existing.model_copy(deep=True)
                probe.transition_to(ref.state)
                ref = ref.model_copy(update={"state": probe.state})

        manifest.write_text(ref.model_dump_json(indent=2), encoding="utf-8")
        return ref

    def get(self, artifact_id: str, version: str) -> tuple[ArtifactRef, bytes]:
        ref = self.head(artifact_id, version)
        ref.ensure_readable()
        content_path = self._version_dir(artifact_id, version) / "content.bin"
        content = content_path.read_bytes()
        actual = self.checksum(content)
        if actual.value != ref.checksum.value:
            raise ChecksumMismatchError(
                f"checksum mismatch for {artifact_id}@{version}"
            )
        return ref, content

    def head(self, artifact_id: str, version: str) -> ArtifactRef:
        manifest = self._version_dir(artifact_id, version) / "manifest.json"
        if not manifest.exists():
            raise ArtifactNotFoundError(f"{artifact_id}@{version} not found")
        return ArtifactRef.model_validate_json(manifest.read_text(encoding="utf-8"))

    def list_versions(self, artifact_id: str) -> list[str]:
        artifact_dir = self._root / artifact_id
        if not artifact_dir.exists():
            return []
        return sorted(p.name for p in artifact_dir.iterdir() if p.is_dir())
