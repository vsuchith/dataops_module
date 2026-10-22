"""Contract validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError as PydanticValidationError

from src.dataops.domain.artifact import ArtifactRef
from src.dataops.domain.dataset import DatasetVersion
from src.dataops.domain.errors import ValidationError
from src.dataops.domain.lineage import LineageEdge
from src.dataops.domain.quality import QualityReport

T = TypeVar("T", bound=BaseModel)

_MODEL_BY_NAME: dict[str, Type[BaseModel]] = {
    "artifact_ref": ArtifactRef,
    "lineage_edge": LineageEdge,
    "quality_report": QualityReport,
    "dataset_version": DatasetVersion,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_contract(model_name: str, payload: dict[str, Any]) -> BaseModel:
    model = _MODEL_BY_NAME.get(model_name)
    if model is None:
        raise ValidationError(f"unknown contract model: {model_name}")
    try:
        return model.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc


def parse_contract_file(model_name: str, path: Path) -> BaseModel:
    return parse_contract(model_name, load_json(path))
