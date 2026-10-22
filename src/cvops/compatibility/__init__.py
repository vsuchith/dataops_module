"""CVOps compatibility layer — unstructured manifest specs (E3)."""

from __future__ import annotations

from src.cvops.compatibility.manifest import (
    build_manifest_payload,
    ingest_manifest,
    load_fixture_manifest,
    manifest_version_id,
    materialize_manifest_artifact,
    record_manifest_lineage,
    register_manifest_dataset,
)
from src.cvops.compatibility.settings_bridge import (
    cvops_settings_snapshot,
    default_cvops_profile,
)
from src.cvops.compatibility.specs import (
    CvopsProfile,
    ImageSourceSpec,
    ManifestDatasetSpec,
)

__all__ = [
    "CvopsProfile",
    "ImageSourceSpec",
    "ManifestDatasetSpec",
    "build_manifest_payload",
    "cvops_settings_snapshot",
    "default_cvops_profile",
    "ingest_manifest",
    "load_fixture_manifest",
    "manifest_version_id",
    "materialize_manifest_artifact",
    "record_manifest_lineage",
    "register_manifest_dataset",
]
