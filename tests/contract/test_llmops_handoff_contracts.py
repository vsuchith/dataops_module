"""LLMOps handoff contract fixtures (E4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.llmops.compatibility.handoff import HandoffValidationError, parse_handoff_contract

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MANIFEST = Path(__file__).resolve().parent / "fixtures-manifest-llmops.json"


def _load_manifest() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", _load_manifest())
def test_valid_llmops_handoff_fixtures(case: dict) -> None:
    for name in case["valid"]:
        payload = json.loads((FIXTURES / "valid" / name).read_text(encoding="utf-8"))
        model = parse_handoff_contract(case["model"], payload)
        assert model is not None


@pytest.mark.parametrize("case", [c for c in _load_manifest() if c["invalid"]])
def test_invalid_llmops_handoff_fixtures(case: dict) -> None:
    for name in case["invalid"]:
        payload = json.loads((FIXTURES / "invalid" / name).read_text(encoding="utf-8"))
        with pytest.raises(HandoffValidationError):
            parse_handoff_contract(case["model"], payload)
