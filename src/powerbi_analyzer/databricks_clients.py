# src/powerbi_analyzer/databricks_clients.py
"""Real SDK-backed clients. Implemented in a later task; keeping import paths stable now."""

from __future__ import annotations

from typing import Any

from powerbi_analyzer.collectors._sql import SqlExecutor


class SdkSqlExecutor(SqlExecutor):
    def __init__(self, *, profile: str) -> None:
        self.profile = profile

    def execute(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError("SdkSqlExecutor lands when the SDK plumbing task runs")

    def describe_extended(self, table: str) -> dict[str, Any]:
        raise NotImplementedError("SdkSqlExecutor lands when the SDK plumbing task runs")


class SdkWorkspaceClient:
    def __init__(self, *, profile: str) -> None:
        self.profile = profile

    def get_warehouse(self, warehouse_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def workspace_region(self) -> str:
        raise NotImplementedError
