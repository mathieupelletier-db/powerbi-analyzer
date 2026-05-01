"""Real Databricks clients backed by databricks-sdk + databricks-sql-connector."""

from __future__ import annotations

import os
from typing import Any

from databricks import sql as dbsql
from databricks.sdk import WorkspaceClient

from powerbi_analyzer.collectors._sql import SqlExecutor


class SdkSqlExecutor(SqlExecutor):
    def __init__(self, *, profile: str) -> None:
        self.profile = profile
        self._wc = WorkspaceClient(profile=profile)
        cfg = self._wc.config
        self._conn = dbsql.connect(
            server_hostname=cfg.host.replace("https://", ""),
            http_path=os.environ.get("PBA_HTTP_PATH", ""),  # set per-warehouse at run time
            access_token=cfg.token,
        )

    def execute(self, query: str) -> list[dict[str, Any]]:
        with self._conn.cursor() as cur:
            cur.execute(query)
            desc = cur.description or []
            cols = [d[0] for d in desc]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def describe_extended(self, table: str) -> dict[str, Any]:
        rows = self.execute(f"DESCRIBE EXTENDED {table}")
        out: dict[str, Any] = {
            "clustering_columns": [],
            "clustering_kind": "none",
            "last_optimize_at": None,
            "last_vacuum_at": None,
            "predictive_optimization": False,
            "size_bytes": None,
            "is_materialized_view": False,
            "has_column_stats": False,
        }
        for r in rows:
            k = (r.get("col_name") or "").strip().lower()
            v = r.get("data_type") or r.get("comment")
            if k == "clusteringcolumns":
                out["clustering_columns"] = (v or "").strip("[]").split(",") if v else []
                out["clustering_kind"] = "liquid" if out["clustering_columns"] else "none"
            elif k == "predictiveoptimization":
                out["predictive_optimization"] = str(v).lower() == "enabled"
            elif k == "type" and v == "MATERIALIZED_VIEW":
                out["is_materialized_view"] = True
        try:
            detail = self.execute(f"DESCRIBE DETAIL {table}")
            if detail:
                d = detail[0]
                out["size_bytes"] = d.get("sizeInBytes")
                out["last_optimize_at"] = d.get("lastModified")
        except Exception:
            pass
        return out


class SdkWorkspaceClient:
    def __init__(self, *, profile: str) -> None:
        self.profile = profile
        self._wc = WorkspaceClient(profile=profile)

    def get_warehouse(self, warehouse_id: str) -> dict[str, Any]:
        wh = self._wc.warehouses.get(warehouse_id)
        raw: dict[str, Any] = dict(wh.as_dict())
        return raw

    def workspace_region(self) -> str:
        host = self._wc.config.host or ""
        # crude region inference from host; replace with config when present
        if ".cloud.databricks.com" in host:
            return os.environ.get("PBA_DATABRICKS_REGION", "us-east-1")
        if ".azuredatabricks.net" in host:
            return os.environ.get("PBA_DATABRICKS_REGION", "eastus")
        if ".gcp.databricks.com" in host:
            return os.environ.get("PBA_DATABRICKS_REGION", "us-central1")
        return "unknown"
