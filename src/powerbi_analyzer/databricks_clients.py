"""Real Databricks clients backed by databricks-sdk + databricks-sql-connector."""

from __future__ import annotations

import os
from typing import Any

from databricks import sql as dbsql
from databricks.sdk import WorkspaceClient

from powerbi_analyzer.collectors._sql import SqlExecutor


class SdkSqlExecutor(SqlExecutor):
    def __init__(self, *, profile: str, warehouse_id: str | None = None) -> None:
        self.profile = profile
        self.warehouse_id = warehouse_id
        self._wc = WorkspaceClient(profile=profile)
        # Resolve http_path eagerly so we fail fast with a useful error rather
        # than hitting databricks-sql-connector's destructor bug
        # (Connection.__del__ raises AttributeError when __init__ fails).
        explicit = os.environ.get("PBA_HTTP_PATH", "").strip()
        if explicit:
            self._http_path = explicit
        elif warehouse_id:
            self._http_path = f"/sql/1.0/warehouses/{warehouse_id}"
        else:
            raise ValueError(
                "Cannot determine Databricks SQL HTTP path: pass --warehouse-id "
                "(pba databricks) or set PBA_HTTP_PATH=/sql/1.0/warehouses/<id>."
            )
        # Lazy: connect on first query so import-time errors stay manageable.
        self._conn: Any | None = None

    def _connection(self) -> Any:
        if self._conn is None:
            cfg = self._wc.config
            host = (cfg.host or "").replace("https://", "").rstrip("/")
            if not host:
                raise ValueError(
                    f"Databricks profile {self.profile!r} has no host configured."
                )
            self._conn = dbsql.connect(
                server_hostname=host,
                http_path=self._http_path,
                access_token=cfg.token,
            )
        return self._conn

    def execute(self, query: str) -> list[dict[str, Any]]:
        with self._connection().cursor() as cur:
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
