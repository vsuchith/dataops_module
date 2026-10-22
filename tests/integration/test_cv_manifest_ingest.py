"""Integration test: offline CV manifest ingest via kernel."""

from pathlib import Path

from src.cvops.compatibility.manifest import ingest_manifest, load_fixture_manifest
from src.cvops.compatibility.settings_bridge import default_cvops_profile
from src.dataops.integrations.local import LocalBackend


def test_cv_manifest_fixture_to_kernel_artifact(tmp_path: Path) -> None:
    profile = default_cvops_profile()
    root = Path(__file__).resolve().parents[1]
    entries = load_fixture_manifest(root / "fixtures" / "cvops" / "images_manifest.json")

    backend = LocalBackend.create(tmp_path)
    try:
        manifest = profile.dataset("manifest")
        result = ingest_manifest(
            backend,
            profile,
            entries,
            version_id="v1",
            run_id="run-cv-integration",
        )
        assert result["kernel_artifact_id"] == manifest.artifact_id
        assert result["kernel_dataset_id"] == manifest.dataset_id

        stored, _ = backend.artifact_store.get(manifest.artifact_id, "v1")
        assert stored.kind.value == "generic"
        assert stored.media_type == "application/json"
    finally:
        backend.close()
