"""Operational acceptance: cvops profile offline manifest ingest."""

from pathlib import Path

from src.cvops.compatibility.annotation import ingest_annotations
from src.cvops.compatibility.manifest import ingest_manifest, load_fixture_manifest
from src.cvops.compatibility.model_stub import (
    materialize_detection_stub_artifact,
    run_deterministic_detection_stub,
)
from src.cvops.compatibility.settings_bridge import default_cvops_profile
from src.dataops.integrations.local import LocalBackend


def test_cvops_profile_offline_smoke(tmp_path: Path) -> None:
    profile = default_cvops_profile()
    root = Path(__file__).resolve().parents[1]
    entries = load_fixture_manifest(root / "fixtures" / "cvops" / "images_manifest.json")
    backend = LocalBackend.create(tmp_path)
    version_id = "v-cv-smoke"
    try:
        manifest_result = ingest_manifest(
            backend,
            profile,
            entries,
            version_id=version_id,
            run_id="run-cv-smoke",
        )
        manifest = profile.dataset("manifest")
        stored, _ = backend.artifact_store.get(manifest.artifact_id, version_id)
        assert stored.artifact_id == manifest_result["kernel_artifact_id"]

        annotation_result = ingest_annotations(
            backend,
            profile,
            entries,
            manifest_artifact_id=manifest_result["kernel_artifact_id"],
            manifest_version=version_id,
            version_id=version_id,
            run_id="run-cv-annotations",
        )
        assert annotation_result["kernel_dataset_id"] == "cv.annotations"

        detections = run_deterministic_detection_stub(entries)
        assert len(detections) == len(entries)
        stub_result = materialize_detection_stub_artifact(
            backend,
            manifest_artifact_id=manifest_result["kernel_artifact_id"],
            manifest_version=version_id,
            manifest_entries=entries,
            version_id=version_id,
            run_id="run-cv-stub",
        )
        assert stub_result["detections"][0]["image_id"] == entries[0]["image_id"]
    finally:
        backend.close()
