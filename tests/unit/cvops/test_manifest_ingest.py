"""Offline manifest ingest via DataOps kernel."""

from pathlib import Path

import pytest

from src.cvops.compatibility.manifest import (
    build_manifest_payload,
    ingest_manifest,
    load_fixture_manifest,
    manifest_version_id,
)
from src.cvops.compatibility.settings_bridge import default_cvops_profile
from src.dataops.integrations.local import LocalBackend


def test_build_manifest_payload_requires_entries() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_manifest_payload([])


def test_fixture_manifest_loads() -> None:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "fixtures" / "cvops" / "images_manifest.json"
    entries = load_fixture_manifest(fixture)
    assert len(entries) == 3
    assert entries[0]["image_id"] == "img-001"


def test_ingest_manifest_registers_artifact_dataset_lineage(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "fixtures" / "cvops" / "images_manifest.json"
    entries = load_fixture_manifest(fixture)
    profile = default_cvops_profile()
    backend = LocalBackend.create(tmp_path)

    try:
        result = ingest_manifest(
            backend,
            profile,
            entries,
            version_id="v-test",
            run_id="run-cv-test",
        )
        manifest = profile.dataset("manifest")
        loaded_ref, content = backend.artifact_store.get(
            manifest.artifact_id,
            "v-test",
        )
        assert loaded_ref.metadata["image_count"] == "3"
        assert len(content) > 0

        dataset = backend.dataset_catalog.get(manifest.dataset_id, "v-test")
        assert dataset.modality.value == "image_collection"
        assert manifest.artifact_id in dataset.physical_artifact_ids

        upstream = backend.lineage_store.list_upstream(
            manifest.artifact_id,
            "v-test",
        )
        assert len(upstream) == 1
        assert upstream[0].operation.value == "ingest"
        assert result["kernel_quality_report_id"].startswith("qr-")
    finally:
        backend.close()


def test_manifest_version_id_is_content_addressed() -> None:
    entries_a = [
        {"image_id": "a", "original_path": "lakefs://cv-data/dev/a.jpg", "format": "jpg"}
    ]
    entries_b = [
        {"image_id": "b", "original_path": "lakefs://cv-data/dev/b.png", "format": "png"}
    ]
    assert manifest_version_id(entries_a) != manifest_version_id(entries_b)
    assert manifest_version_id(entries_a) == manifest_version_id(entries_a.copy())


def test_repeated_ingest_same_content_is_idempotent(tmp_path: Path) -> None:
    entries = [
        {"image_id": "a", "original_path": "lakefs://cv-data/dev/a.jpg", "format": "jpg"}
    ]
    profile = default_cvops_profile()
    backend = LocalBackend.create(tmp_path)
    version_id = manifest_version_id(entries)
    manifest = profile.dataset("manifest")

    try:
        ingest_manifest(backend, profile, entries, version_id=version_id, run_id="run-1")
        ingest_manifest(backend, profile, entries, version_id=version_id, run_id="run-2")
        versions = backend.artifact_store.list_versions(manifest.artifact_id)
        assert versions == [version_id]
    finally:
        backend.close()


def test_changed_manifest_content_creates_new_version(tmp_path: Path) -> None:
    profile = default_cvops_profile()
    backend = LocalBackend.create(tmp_path)
    manifest = profile.dataset("manifest")
    entries_v1 = [
        {"image_id": "a", "original_path": "lakefs://cv-data/dev/a.jpg", "format": "jpg"}
    ]
    entries_v2 = [
        {"image_id": "b", "original_path": "lakefs://cv-data/dev/b.png", "format": "png"}
    ]

    try:
        ingest_manifest(
            backend,
            profile,
            entries_v1,
            version_id=manifest_version_id(entries_v1),
            run_id="run-1",
        )
        ingest_manifest(
            backend,
            profile,
            entries_v2,
            version_id=manifest_version_id(entries_v2),
            run_id="run-2",
        )
        assert len(backend.artifact_store.list_versions(manifest.artifact_id)) == 2
    finally:
        backend.close()
