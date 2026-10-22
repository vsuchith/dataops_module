"""Trino adapter — wraps TrinoResource without changing its API."""

from __future__ import annotations

from typing import Any, List


class TrinoQueryAdapter:
    def __init__(self, trino_resource: Any) -> None:
        self._trino = trino_resource

    def execute_query(self, query: str) -> List[Any]:
        return self._trino.execute_query(query)

    def execute_ddl(self, query: str) -> None:
        self._trino.execute_ddl(query)

    def table_exists(self, table_name: str) -> bool:
        return self._trino.table_exists(table_name)

    def get_count(self, table_name: str) -> int:
        return self._trino.get_count(table_name)
