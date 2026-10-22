"""Provider adapter delegation tests."""

from unittest.mock import MagicMock

from src.dataops.domain.artifact import ArtifactKind, ArtifactState, Checksum
from src.dataops.integrations.providers import (
    LakeFSArtifactStoreAdapter,
    MinIOObjectStoreAdapter,
    TrinoQueryAdapter,
)


def test_lakefs_adapter_delegates_upload_and_list() -> None:
    lakefs = MagicMock()
    lakefs.commit.return_value = {"id": "commit-1"}
    adapter = LakeFSArtifactStoreAdapter(lakefs, repo="repo", branch="main")

    adapter.upload_bytes("path/key", b"data", message="test")
    lakefs.upload_content.assert_called_once_with("repo", "main", b"data", "path/key")
    lakefs.commit.assert_called_once()

    lakefs.list_objects.return_value = ["a", "b"]
    assert adapter.list_keys("prefix/") == ["a", "b"]
    lakefs.list_objects.assert_called_with("repo", "main", prefix="prefix/")


def test_lakefs_adapter_builds_artifact_ref() -> None:
    lakefs = MagicMock()
    lakefs.get_commit.return_value = {"id": "c1"}
    lakefs.get_object_url.return_value = "http://lakefs/obj"
    adapter = LakeFSArtifactStoreAdapter(lakefs, repo="repo", branch="dev")

    ref = adapter.to_artifact_ref(
        artifact_id="art",
        version="v1",
        key="k",
        checksum=Checksum(value="a" * 64),
        state=ArtifactState.PUBLISHED,
    )
    assert ref.kind == ArtifactKind.GENERIC
    assert ref.provider_replay.lakefs_commit == "c1"


def test_minio_adapter_delegates() -> None:
    minio = MagicMock()
    adapter = MinIOObjectStoreAdapter(minio)
    adapter.upload_file("b", "k", "/tmp/f")
    minio.upload_file.assert_called_once_with("b", "k", "/tmp/f")


def test_trino_adapter_delegates() -> None:
    trino = MagicMock()
    trino.execute_query.return_value = [(1,)]
    adapter = TrinoQueryAdapter(trino)
    assert adapter.execute_query("SELECT 1") == [(1,)]
    trino.execute_query.assert_called_once_with("SELECT 1")
