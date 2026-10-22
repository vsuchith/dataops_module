"""Genera handoff contracts — frozen at E4 (ADR-008)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticValidationError, field_validator, model_validator

HANDOFF_SCHEMA_VERSION = "1.0.0"


class HandoffValidationError(ValueError):
    """Raised when a handoff contract payload is invalid."""


class DocumentEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    uri: str
    checksum: str
    media_type: str

    @field_validator("source_id", "uri", "checksum", "media_type")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v


class DocumentManifestRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_id: str
    version: str
    documents: list[DocumentEntry]
    partition_strategy: str = "by_document"

    @field_validator("manifest_id", "version")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v

    @field_validator("documents")
    @classmethod
    def documents_non_empty(cls, v: list[DocumentEntry]) -> list[DocumentEntry]:
        if not v:
            raise ValueError("document manifest requires at least one document")
        return v


class CanonicalElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    element_type: str
    content: str
    source_document_id: str
    page: Optional[int] = None
    confidence: float = 1.0

    @field_validator("element_id", "element_type", "content", "source_document_id")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v


class ElementSetRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_set_id: str
    version: str
    parent_manifest_ref: str
    extraction_profile: str
    elements: list[CanonicalElement]

    @field_validator("element_set_id", "version", "parent_manifest_ref", "extraction_profile")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v

    @field_validator("elements")
    @classmethod
    def elements_non_empty(cls, v: list[CanonicalElement]) -> list[CanonicalElement]:
        if not v:
            raise ValueError("element set requires at least one element")
        return v


class CorpusVersionRef(BaseModel):
    """Immutable corpus version pin for Genera index builds (ADR-008)."""

    model_config = ConfigDict(extra="forbid")

    corpus_id: str
    version: str
    schema_version: str = HANDOFF_SCHEMA_VERSION
    document_manifest_refs: list[str]
    element_set_refs: list[str]
    embedding_set_refs: list[str] = Field(default_factory=list)
    index_ref: Optional[str] = None
    checksum: str
    parser_profile: str
    security_labels: list[str] = Field(default_factory=list)
    quality_report_id: Optional[str] = None
    lineage_run_id: Optional[str] = None

    @field_validator("corpus_id", "version", "checksum", "parser_profile")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v

    @field_validator("document_manifest_refs", "element_set_refs")
    @classmethod
    def refs_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("corpus version requires manifest and element refs")
        return v

    @model_validator(mode="after")
    def schema_version_must_match_pin(self) -> CorpusVersionRef:
        if self.schema_version != HANDOFF_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported handoff schema_version {self.schema_version!r}; "
                f"expected {HANDOFF_SCHEMA_VERSION}"
            )
        return self


class DerivedArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    version: str
    recipe_id: str
    recipe_version: str
    producer: Literal["llmops", "genera"]
    input_refs: list[str]
    output_uri: str
    checksum: str
    semantic_owner: str

    @field_validator(
        "artifact_id",
        "version",
        "recipe_id",
        "recipe_version",
        "output_uri",
        "checksum",
        "semantic_owner",
    )
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v

    @field_validator("input_refs")
    @classmethod
    def inputs_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("derived artifact requires at least one input ref")
        return v


_HANDOFF_MODELS = {
    "corpus_version_ref": CorpusVersionRef,
    "document_manifest_ref": DocumentManifestRef,
    "element_set_ref": ElementSetRef,
    "derived_artifact_ref": DerivedArtifactRef,
}


def parse_handoff_contract(model_name: str, payload: dict) -> BaseModel:
    model = _HANDOFF_MODELS.get(model_name)
    if model is None:
        raise HandoffValidationError(f"unknown handoff model: {model_name}")
    try:
        return model.model_validate(payload)
    except PydanticValidationError as exc:
        raise HandoffValidationError(str(exc)) from exc
