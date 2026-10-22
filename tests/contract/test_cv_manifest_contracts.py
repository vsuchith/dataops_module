"""CV manifest kernel contract fixtures (E3)."""

import json
from pathlib import Path

from src.dataops.application.validation import parse_contract

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "valid"


def test_cv_manifest_artifact_contract() -> None:
    payload = json.loads((FIXTURES / "cv_manifest_artifact.json").read_text(encoding="utf-8"))
    model = parse_contract("artifact_ref", payload)
    assert model.artifact_id == "cv.image_manifest"


def test_cv_dataset_version_image_collection_contract() -> None:
    payload = json.loads(
        (FIXTURES / "dataset_version_image_collection.json").read_text(encoding="utf-8")
    )
    model = parse_contract("dataset_version", payload)
    assert model.modality.value == "image_collection"


def test_cv_manifest_lineage_edge_contract() -> None:
    payload = json.loads(
        (FIXTURES / "lineage_edge_cv_manifest.json").read_text(encoding="utf-8")
    )
    model = parse_contract("lineage_edge", payload)
    assert model.operation.value == "ingest"
