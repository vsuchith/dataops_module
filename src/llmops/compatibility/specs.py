"""Reference corpus profile specs (E4)."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DocumentFormat(str, Enum):
    TXT = "txt"
    MARKDOWN = "markdown"
    HTML = "html"


class DocumentSourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    format: DocumentFormat
    uri_pattern: str
    description: Optional[str] = None

    @field_validator("name", "uri_pattern")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v


class CorpusDatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    corpus_id: str
    artifact_id: str
    catalog_table: str
    source_ref: Optional[str] = None
    schema_ref: Optional[str] = None

    @field_validator("name", "corpus_id", "artifact_id", "catalog_table")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v


class QualityCheckSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    severity: str = "critical"
    rule: str


class ReferenceCorpusProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    version: str = "1.0.0"
    parser_profile: str = "reference-txt-md-html-v1"
    sources: list[DocumentSourceSpec] = Field(default_factory=list)
    datasets: list[CorpusDatasetSpec] = Field(default_factory=list)
    quality_checks: list[QualityCheckSpec] = Field(default_factory=list)
    security_labels: list[str] = Field(default_factory=lambda: ["internal"])

    @model_validator(mode="after")
    def validate_references(self) -> ReferenceCorpusProfile:
        source_names = {s.name for s in self.sources}
        for ds in self.datasets:
            if ds.source_ref and ds.source_ref not in source_names:
                raise ValueError(
                    f"dataset {ds.name} references unknown source {ds.source_ref!r}"
                )
        return self

    def dataset(self, name: str) -> CorpusDatasetSpec:
        for ds in self.datasets:
            if ds.name == name:
                return ds
        raise KeyError(f"dataset {name!r} not in profile {self.profile_id}")

    def source(self, name: str) -> DocumentSourceSpec:
        for src in self.sources:
            if src.name == name:
                return src
        raise KeyError(f"source {name!r} not in profile {self.profile_id}")
