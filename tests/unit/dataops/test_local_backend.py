"""Local reference backend tests (ADR-007)."""

from pathlib import Path

import pytest

from src.dataops.domain.artifact import ArtifactKind, ArtifactRef, ArtifactState
from src.dataops.domain.dataset import DatasetModality, DatasetVersion
from src.dataops.domain.lineage import LineageEdge, LineageOperation
from src.dataops.integrations.local import LocalBackend
from src.dataops.integrations.local.filesystem_store import LocalFilesystemArtifactStore


@pytest.fixture
def backend(tmp_path: Path) -> LocalBackend:
    return LocalBackend.create(tmp_path)


def test_artifact_roundtrip(backend: LocalBackend) -> None:
    content = b"kernel-bytes"
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id="art-local",
        version="v1",
        kind=ArtifactKind.STRUCTURED_TABLE,
        uri="file:///local/art-local/v1",
        checksum=checksum,
        state=ArtifactState.VALIDATED,
    )
    stored = backend.artifact_store.put(ref, content)
    assert stored.checksum.value
    loaded_ref, loaded_bytes = backend.artifact_store.get("art-local", "v1")
    assert loaded_bytes == content
    assert loaded_ref.checksum == stored.checksum


def test_quality_evaluator_passes(backend: LocalBackend) -> None:
    content = b"quality-payload"
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id="art-q",
        version="v1",
        kind=ArtifactKind.GENERIC,
        uri="file:///local/art-q",
        checksum=checksum,
        state=ArtifactState.PUBLISHED,
    )
    stored = backend.artifact_store.put(ref, content)
    report = backend.quality_evaluator.evaluate(stored, content)
    assert report.pass_fail is True


def test_commit_lifecycle_updates_state(backend: LocalBackend) -> None:
    content = b"lifecycle-bytes"
    checksum = LocalFilesystemArtifactStore.checksum(content)
    ref = ArtifactRef(
        artifact_id="art-life",
        version="v1",
        kind=ArtifactKind.GENERIC,
        uri="file:///local/art-life",
        checksum=checksum,
        state=ArtifactState.DRAFT,
    )
    stored = backend.artifact_store.put(ref, content)
    validated = stored.model_copy(update={"state": ArtifactState.VALIDATED})
    updated = backend.artifact_store.commit_lifecycle(validated)
    assert updated.state == ArtifactState.VALIDATED


def test_dataset_and_lineage(backend: LocalBackend) -> None:
    version = DatasetVersion(
        dataset_id="ds-1",
        version_id="v1",
        modality=DatasetModality.STRUCTURED,
        physical_artifact_ids=["art-local"],
    )
    backend.dataset_catalog.register(version)
    loaded = backend.dataset_catalog.get("ds-1", "v1")
    assert loaded.dataset_id == "ds-1"

    edge = LineageEdge(
        source_artifact_id="art-a",
        source_version="v1",
        target_artifact_id="art-b",
        target_version="v1",
        operation=LineageOperation.TRANSFORM,
        run_id="run-1",
    )
    backend.lineage_store.record_edge(edge)
    upstream = backend.lineage_store.list_upstream("art-b", "v1")
    assert len(upstream) == 1
    assert upstream[0].source_artifact_id == "art-a"
