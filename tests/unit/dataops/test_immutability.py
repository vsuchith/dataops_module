"""ADR-002 immutability regression tests."""

from pathlib import Path

import pytest

from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState
from src.dataops.domain.errors import ImmutableVersionError
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore


def _published_ref(artifact_id: str, version: str, checksum_value: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        version=version,
        kind=ArtifactKind.GENERIC,
        uri=f"file:///local/{artifact_id}/{version}",
        checksum=LocalFilesystemArtifactStore.checksum(checksum_value.encode()),
        state=ArtifactState.PUBLISHED,
    )


def test_put_is_idempotent_for_same_content(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    content = b"immutable-bytes"
    ref = _published_ref("art-1", "v1", "immutable-bytes")
    first = store.put(ref, content)
    second = store.put(ref, content)
    assert first.checksum == second.checksum
    _, loaded = store.get("art-1", "v1")
    assert loaded == content


def test_put_rejects_conflicting_content_for_same_version(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    ref = _published_ref("art-1", "v1", "first")
    store.put(ref, b"first")
    with pytest.raises(ImmutableVersionError):
        store.put(_published_ref("art-1", "v1", "second"), b"second")


def test_lineage_edge_key_includes_run_id() -> None:
    base = dict(
        source_artifact_id="a",
        source_version="v1",
        target_artifact_id="b",
        target_version="v1",
        operation=LineageOperation.TRANSFORM,
    )
    edge_one = LineageEdge(**base, run_id="run-1")
    edge_two = LineageEdge(**base, run_id="run-2")
    assert edge_one.edge_key() != edge_two.edge_key()


def test_lineage_preserves_edges_from_separate_runs(tmp_path: Path) -> None:
    backend = LocalBackend.create(tmp_path)
    base = dict(
        source_artifact_id="art-a",
        source_version="v1",
        target_artifact_id="art-b",
        target_version="v1",
        operation=LineageOperation.TRANSFORM,
    )
    backend.lineage_store.record_edge(LineageEdge(**base, run_id="run-1"))
    backend.lineage_store.record_edge(LineageEdge(**base, run_id="run-2"))
    upstream = backend.lineage_store.list_upstream("art-b", "v1")
    assert {e.run_id for e in upstream} == {"run-1", "run-2"}
