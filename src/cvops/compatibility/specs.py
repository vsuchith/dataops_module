"""CVOps profile specs — inline defaults until E5 profiles/object_detection."""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StorageKind(str, Enum):
    LAKEFS = "lakefs"
    S3 = "s3"


class ImageSourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    storage_kind: StorageKind = StorageKind.LAKEFS
    uri_prefix: str
    supported_formats: list[str] = Field(
        default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp"]
    )
    description: Optional[str] = None

    @field_validator("name", "uri_prefix")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v

    @field_validator("supported_formats")
    @classmethod
    def formats_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("supported_formats must not be empty")
        return v


class ManifestDatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    dataset_id: str
    artifact_id: str
    catalog_table: str
    source_ref: Optional[str] = None
    schema_ref: Optional[str] = None

    @field_validator("name", "dataset_id", "artifact_id", "catalog_table")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v


class QualityCheckSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    severity: Literal["critical", "warning"] = "critical"
    rule: str


class PromotionPolicySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_stage: str = "Production"
    require_quality_pass: bool = True
    min_training_samples: int = 50


class CvopsProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    version: str = "1.0.0"
    lakefs_repo: str = "cv-data"
    lakefs_branch: str = "dev"
    raw_prefix: str = "raw/images/"
    sources: list[ImageSourceSpec] = Field(default_factory=list)
    datasets: list[ManifestDatasetSpec] = Field(default_factory=list)
    quality_checks: list[QualityCheckSpec] = Field(default_factory=list)
    promotion_policy: PromotionPolicySpec = Field(default_factory=PromotionPolicySpec)

    @model_validator(mode="after")
    def validate_references(self) -> CvopsProfile:
        source_names = {s.name for s in self.sources}
        for ds in self.datasets:
            if ds.source_ref and ds.source_ref not in source_names:
                raise ValueError(
                    f"dataset {ds.name} references unknown source {ds.source_ref!r}"
                )
        return self

    def dataset(self, name: str) -> ManifestDatasetSpec:
        for ds in self.datasets:
            if ds.name == name:
                return ds
        raise KeyError(f"dataset {name!r} not in profile {self.profile_id}")

    def source(self, name: str) -> ImageSourceSpec:
        for src in self.sources:
            if src.name == name:
                return src
        raise KeyError(f"source {name!r} not in profile {self.profile_id}")
