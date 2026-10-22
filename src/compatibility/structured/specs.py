"""Generic structured DataOps specification types."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BatchFormat(str, Enum):
    CSV = "csv"
    PARQUET = "parquet"


class CdcFormat(str, Enum):
    JSON = "json"


class SourceKind(str, Enum):
    BATCH = "batch"
    CDC = "cdc"


class SourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    kind: SourceKind = SourceKind.BATCH
    format: BatchFormat
    uri_pattern: str = ""
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source name required")
        return v

    @model_validator(mode="after")
    def kind_must_be_batch(self) -> SourceSpec:
        if self.kind != SourceKind.BATCH:
            raise ValueError('batch source kind must be "batch"')
        return self


class CdcSourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    kind: SourceKind = SourceKind.CDC
    topic: str
    primary_key: str
    format: CdcFormat = CdcFormat.JSON
    description: Optional[str] = None

    @field_validator("name", "topic", "primary_key")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v

    @model_validator(mode="after")
    def kind_must_be_cdc(self) -> CdcSourceSpec:
        if self.kind != SourceKind.CDC:
            raise ValueError('cdc source kind must be "cdc"')
        return self


class DatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    catalog_table: str
    primary_key: str = "id"
    label_column: Optional[str] = None
    source_ref: Optional[str] = None
    partitions: list[str] = Field(default_factory=list)
    schema_ref: Optional[str] = None

    @field_validator("name", "catalog_table", "primary_key")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v


class TransformSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    from_dataset: str
    to_dataset: str
    description: Optional[str] = None


class QualityCheckSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    severity: str = "critical"
    rule: str


class PromotionPolicySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_stage: str = "Production"
    require_quality_pass: bool = True
    min_training_samples: int = 50


class StructuredProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    version: str = "1.0.0"
    sources: list[SourceSpec] = Field(default_factory=list)
    cdc_sources: list[CdcSourceSpec] = Field(default_factory=list)
    datasets: list[DatasetSpec] = Field(default_factory=list)
    transforms: list[TransformSpec] = Field(default_factory=list)
    quality_checks: list[QualityCheckSpec] = Field(default_factory=list)
    promotion_policy: PromotionPolicySpec = Field(default_factory=PromotionPolicySpec)

    @model_validator(mode="after")
    def validate_references(self) -> StructuredProfile:
        source_names = {s.name for s in self.sources}
        dataset_names = {d.name for d in self.datasets}
        for ds in self.datasets:
            if ds.source_ref and ds.source_ref not in source_names:
                raise ValueError(
                    f"dataset {ds.name} references unknown source {ds.source_ref!r}"
                )
        for tx in self.transforms:
            if tx.from_dataset not in dataset_names:
                raise ValueError(
                    f"transform {tx.name} references unknown dataset {tx.from_dataset!r}"
                )
            if tx.to_dataset not in dataset_names:
                raise ValueError(
                    f"transform {tx.name} references unknown dataset {tx.to_dataset!r}"
                )
        return self

    def dataset(self, name: str) -> DatasetSpec:
        for ds in self.datasets:
            if ds.name == name:
                return ds
        raise KeyError(f"dataset {name!r} not in profile {self.profile_id}")

    def source(self, name: str) -> SourceSpec:
        for src in self.sources:
            if src.name == name:
                return src
        raise KeyError(f"source {name!r} not in profile {self.profile_id}")

    def cdc_source(self, name: str) -> CdcSourceSpec:
        for src in self.cdc_sources:
            if src.name == name:
                return src
        raise KeyError(f"cdc source {name!r} not in profile {self.profile_id}")
