"""Lineage graph edges (ADR-002)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, field_validator


class LineageOperation(str, Enum):
    INGEST = "ingest"
    TRANSFORM = "transform"
    TRAIN = "train"
    EMBED = "embed"
    INDEX = "index"
    PROMOTE = "promote"


class LineageEdge(BaseModel):
    source_artifact_id: str
    source_version: str
    target_artifact_id: str
    target_version: str
    operation: LineageOperation
    run_id: str
    metadata: dict[str, str] = {}

    @field_validator("run_id")
    @classmethod
    def run_id_required(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("run_id is required")
        return v

    def edge_key(self) -> str:
        return (
            f"{self.source_artifact_id}@{self.source_version}"
            f"->{self.target_artifact_id}@{self.target_version}:"
            f"{self.operation.value}:{self.run_id}"
        )
