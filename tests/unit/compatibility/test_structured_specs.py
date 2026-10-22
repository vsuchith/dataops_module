"""Structured spec validation tests (E2.2 fail-closed)."""

import pytest
from pydantic import ValidationError

from src.compatibility.structured.specs import CdcSourceSpec


@pytest.mark.parametrize(
    "payload,match",
    [
        (
            {"name": "cdc", "kind": "batch", "topic": "t", "primary_key": "id"},
            "cdc",
        ),
        (
            {"name": "", "kind": "cdc", "topic": "t", "primary_key": "id"},
            "name",
        ),
        (
            {"name": "cdc", "kind": "cdc", "topic": "", "primary_key": "id"},
            "empty",
        ),
        (
            {"name": "cdc", "kind": "cdc", "topic": "t", "primary_key": ""},
            "empty",
        ),
        (
            {
                "name": "cdc",
                "kind": "cdc",
                "topic": "t",
                "primary_key": "id",
                "format": "xml",
            },
            "format",
        ),
        (
            {
                "name": "cdc",
                "kind": "cdc",
                "topic": "t",
                "primary_key": "id",
                "unexpected": True,
            },
            "extra",
        ),
    ],
)
def test_cdc_source_spec_rejects_invalid(payload: dict, match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        CdcSourceSpec.model_validate(payload)
