"""Lineage graph port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.dataops.domain.lineage import LineageEdge


@runtime_checkable
class LineageStore(Protocol):
    def record_edge(self, edge: LineageEdge) -> LineageEdge: ...

    def list_upstream(self, artifact_id: str, version: str) -> list[LineageEdge]: ...

    def list_downstream(self, artifact_id: str, version: str) -> list[LineageEdge]: ...
