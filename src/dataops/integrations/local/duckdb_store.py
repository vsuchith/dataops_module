"""DuckDB-backed dataset catalog and lineage store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import duckdb

from src.dataops.domain.dataset import DatasetVersion
from src.dataops.domain.errors import DataOpsError, ImmutableVersionError
from src.dataops.domain.lineage import LineageEdge


class DuckDBCatalogStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            self._conn = duckdb.connect(database=":memory:")
        else:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(database=str(db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dataset_versions (
                dataset_id VARCHAR,
                version_id VARCHAR,
                payload JSON,
                PRIMARY KEY (dataset_id, version_id)
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lineage_edges (
                edge_key VARCHAR PRIMARY KEY,
                payload JSON
            )
            """
        )

    def register(self, version: DatasetVersion) -> DatasetVersion:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO dataset_versions (dataset_id, version_id, payload)
            VALUES (?, ?, ?)
            """,
            [version.dataset_id, version.version_id, version.model_dump_json()],
        )
        return version

    def get(self, dataset_id: str, version_id: str) -> DatasetVersion:
        row = self._conn.execute(
            """
            SELECT payload FROM dataset_versions
            WHERE dataset_id = ? AND version_id = ?
            """,
            [dataset_id, version_id],
        ).fetchone()
        if not row:
            raise DataOpsError(f"dataset {dataset_id}@{version_id} not found")
        return DatasetVersion.model_validate_json(row[0])

    def record_edge(self, edge: LineageEdge) -> LineageEdge:
        key = edge.edge_key()
        row = self._conn.execute(
            "SELECT payload FROM lineage_edges WHERE edge_key = ?",
            [key],
        ).fetchone()
        if row:
            existing = LineageEdge.model_validate_json(row[0])
            if existing.model_dump() == edge.model_dump():
                return existing
            raise ImmutableVersionError(f"lineage edge conflict for {key}")
        self._conn.execute(
            """
            INSERT INTO lineage_edges (edge_key, payload)
            VALUES (?, ?)
            """,
            [key, edge.model_dump_json()],
        )
        return edge

    def delete_edge(self, edge: LineageEdge) -> None:
        self._conn.execute(
            "DELETE FROM lineage_edges WHERE edge_key = ?",
            [edge.edge_key()],
        )

    def list_upstream(self, artifact_id: str, version: str) -> list[LineageEdge]:
        rows = self._conn.execute("SELECT payload FROM lineage_edges").fetchall()
        edges = [LineageEdge.model_validate_json(r[0]) for r in rows]
        return [
            e
            for e in edges
            if e.target_artifact_id == artifact_id and e.target_version == version
        ]

    def list_downstream(self, artifact_id: str, version: str) -> list[LineageEdge]:
        rows = self._conn.execute("SELECT payload FROM lineage_edges").fetchall()
        edges = [LineageEdge.model_validate_json(r[0]) for r in rows]
        return [
            e
            for e in edges
            if e.source_artifact_id == artifact_id and e.source_version == version
        ]

    def close(self) -> None:
        self._conn.close()
