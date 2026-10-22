"""CVOps profile parity with legacy CVOpsSettings."""

from pathlib import Path

from src.core.config import CVOpsSettings
from src.cvops.compatibility.manifest import load_fixture_manifest
from src.cvops.compatibility.settings_bridge import (
    cvops_settings_snapshot,
    default_cvops_profile,
    manifest_table_fqn,
)


def test_cvops_profile_settings_parity() -> None:
    profile = default_cvops_profile()
    legacy = CVOpsSettings()
    snap = cvops_settings_snapshot(profile)
    assert snap["repo"] == legacy.repo
    assert snap["branch"] == legacy.branch
    assert snap["raw_prefix"] == legacy.raw_prefix
    assert snap["manifest_schema"] == legacy.manifest_schema
    assert snap["manifest_table"] == legacy.manifest_table
    assert snap["manifest_table_fqn"] == manifest_table_fqn(legacy)
    assert int(snap["min_training_samples"]) == legacy.min_training_samples


def test_fixture_manifest_matches_profile_source_prefix() -> None:
    profile = default_cvops_profile()
    source = profile.source("raw_images")
    root = Path(__file__).resolve().parents[1]
    entries = load_fixture_manifest(root / "fixtures" / "cvops" / "images_manifest.json")
    for entry in entries:
        assert entry["original_path"].startswith(source.uri_prefix.split("/raw/")[0])
