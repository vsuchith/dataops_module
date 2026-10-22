"""Dataset version aggregate (minimal E2.1 slice)."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DatasetModality(str, Enum):
    STRUCTURED = "structured"
    IMAGE_COLLECTION = "image_collection"
    TEXT_CORPUS = "text_corpus"


class DatasetVersion(BaseModel):
    dataset_id: str
    version_id: str
    modality: DatasetModality
    physical_artifact_ids: list[str] = Field(default_factory=list)
    schema_or_manifest_ref: Optional[str] = None
    parent_version: Optional[str] = None
    quality_report_id: Optional[str] = None

    @field_validator("dataset_id", "version_id")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v

    @field_validator("physical_artifact_ids")
    @classmethod
    def at_least_one_artifact(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("dataset version requires at least one physical artifact")
        return v
