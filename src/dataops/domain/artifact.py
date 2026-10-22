"""Artifact identity and lifecycle (ADR-002)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.dataops.domain.errors import ValidationError


class ArtifactKind(str, Enum):
    STRUCTURED_TABLE = "structured_table"
    DOCUMENT = "document"
    ELEMENT_SET = "element_set"
    EMBEDDING_SET = "embedding_set"
    MODEL = "model"
    ANNOTATION = "annotation"
    GENERIC = "generic"


class ArtifactState(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    TOMBSTONED = "tombstoned"


_PUBLISHED_STATES = {ArtifactState.PUBLISHED, ArtifactState.DEPRECATED, ArtifactState.TOMBSTONED}


class Checksum(BaseModel):
    algorithm: str = "sha256"
    value: str

    @field_validator("value")
    @classmethod
    def value_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("checksum value is required")
        return v.lower()


class ProviderReplayMetadata(BaseModel):
    """LakeFS/Iceberg/Nessie replay hints — not domain identity owners."""

    lakefs_repo: Optional[str] = None
    lakefs_branch: Optional[str] = None
    lakefs_commit: Optional[str] = None
    iceberg_snapshot: Optional[str] = None
    nessie_ref: Optional[str] = None


class ArtifactRef(BaseModel):
    artifact_id: str
    version: str
    kind: ArtifactKind
    uri: str
    checksum: Checksum
    state: ArtifactState = ArtifactState.DRAFT
    media_type: Optional[str] = None
    schema_ref: Optional[str] = None
    producer_run_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tenant_scope: Optional[str] = None
    security_labels: list[str] = Field(default_factory=list)
    provider_replay: ProviderReplayMetadata = Field(default_factory=ProviderReplayMetadata)

    @field_validator("artifact_id", "version", "uri")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field must not be empty")
        return v

    @model_validator(mode="after")
    def published_requires_checksum(self) -> ArtifactRef:
        if self.state in _PUBLISHED_STATES and not self.checksum.value:
            raise ValueError("published artifacts require a checksum")
        return self

    def identity_key(self) -> str:
        return f"{self.artifact_id}@{self.version}"

    def ensure_readable(self) -> None:
        if self.state == ArtifactState.TOMBSTONED:
            raise ValidationError(f"artifact {self.identity_key()} is tombstoned")

    def transition_to(self, target: ArtifactState) -> None:
        allowed = {
            ArtifactState.DRAFT: {ArtifactState.VALIDATED, ArtifactState.TOMBSTONED},
            ArtifactState.VALIDATED: {ArtifactState.PUBLISHED, ArtifactState.TOMBSTONED},
            ArtifactState.PUBLISHED: {ArtifactState.DEPRECATED, ArtifactState.TOMBSTONED},
            ArtifactState.DEPRECATED: {ArtifactState.TOMBSTONED},
            ArtifactState.TOMBSTONED: set(),
        }
        if target not in allowed[self.state]:
            raise ValidationError(
                f"illegal transition {self.state.value} -> {target.value} for {self.identity_key()}"
            )
        self.state = target
