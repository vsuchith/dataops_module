"""CVOps spec validation tests."""

import pytest
from pydantic import ValidationError

from src.cvops.compatibility.specs import CvopsProfile, ImageSourceSpec, StorageKind


def test_default_profile_loads() -> None:
    from src.cvops.compatibility.settings_bridge import default_cvops_profile

    profile = default_cvops_profile()
    assert profile.profile_id == "object_detection"
    manifest = profile.dataset("manifest")
    assert manifest.dataset_id == "cv.image_collection"
    assert manifest.artifact_id == "cv.image_manifest"


def test_image_source_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        ImageSourceSpec.model_validate(
            {
                "name": "",
                "uri_prefix": "lakefs://cv-data/dev/raw/",
            }
        )


def test_profile_rejects_unknown_source_ref() -> None:
    with pytest.raises(ValidationError, match="unknown source"):
        CvopsProfile.model_validate(
            {
                "profile_id": "bad",
                "sources": [
                    {
                        "name": "raw",
                        "uri_prefix": "lakefs://cv-data/dev/raw/",
                    }
                ],
                "datasets": [
                    {
                        "name": "manifest",
                        "dataset_id": "cv.image_collection",
                        "artifact_id": "cv.image_manifest",
                        "catalog_table": "bronze.cv_image_manifest",
                        "source_ref": "missing",
                    }
                ],
            }
        )


def test_image_source_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="extra"):
        ImageSourceSpec.model_validate(
            {
                "name": "raw",
                "uri_prefix": "lakefs://cv-data/dev/raw/",
                "unexpected": True,
            }
        )


def test_storage_kind_values() -> None:
    source = ImageSourceSpec(
        name="raw",
        storage_kind=StorageKind.S3,
        uri_prefix="s3://cv-raw/",
    )
    assert source.storage_kind == StorageKind.S3
