"""Databricks-side collector — warehouse REST + system tables."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from powerbi_analyzer.collectors._sql import SqlExecutor
from powerbi_analyzer.collectors.base import Collector, CollectorError
from powerbi_analyzer.domain.catalog import (
    CatalogState,
    ClusteringInfo,
    ColumnMetadata,
    ForeignKey,
    TableMetadata,
)
from powerbi_analyzer.domain.warehouse import (
    QueryHistoryEntry,
    WarehouseEvent,
    WarehouseState,
)

GOLD_HINTS = {"gold", "serving", "mart", "marts", "presentation"}
SILVER_HINTS = {"silver", "curated"}
BRONZE_HINTS = {"bronze", "raw", "landing"}


class WorkspaceClient(Protocol):
    def get_warehouse(self, warehouse_id: str) -> dict[str, Any]: ...
    def workspace_region(self) -> str: ...


def _as_dict(value: Any) -> dict[str, Any]:
    """Normalize a STRUCT cell from system.query.history to a plain dict.

    Databricks SQL connector returns STRUCT columns as either a dict (Arrow
    path) or a JSON string (Thrift / cloud-fetch path) depending on connector
    version and warehouse config. Be tolerant of both.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    # Row objects expose .asDict()
    asdict = getattr(value, "asDict", None)
    if callable(asdict):
        result = asdict()
        return result if isinstance(result, dict) else {}
    return {}


def _as_list(value: Any) -> list[Any]:
    """Normalize an ARRAY cell — handles list, JSON string, or None."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return []


def _parse_dt(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def _layer_for(schema: str) -> str:
    s = schema.lower()
    if any(h in s for h in GOLD_HINTS):
        return "gold"
    if any(h in s for h in SILVER_HINTS):
        return "silver"
    if any(h in s for h in BRONZE_HINTS):
        return "bronze"
    return "unknown"


class DatabricksCollector(Collector):
    mode = "databricks"

    def __init__(
        self,
        *,
        warehouse_id: str,
        catalogs: list[str],
        lookback_days: int,
        sql: SqlExecutor,
        ws: WorkspaceClient,
    ) -> None:
        self.warehouse_id = warehouse_id
        self.catalogs = catalogs
        self.lookback_days = lookback_days
        self.sql = sql
        self.ws = ws

    def collect(self) -> tuple[WarehouseState, CatalogState]:
        try:
            wh_payload = self.ws.get_warehouse(self.warehouse_id)
            region = self.ws.workspace_region()
        except Exception as exc:
            raise CollectorError(f"warehouse REST failed: {exc}", mode=self.mode) from exc

        wh_state = self._warehouse_state(wh_payload, region)
        cat_state = self._catalog_state(wh_state)
        return wh_state, cat_state

    def _warehouse_state(self, payload: dict[str, Any], region: str) -> WarehouseState:
        wh_type = (
            "serverless"
            if payload.get("enable_serverless_compute")
            else payload.get("warehouse_type", "PRO").lower()
        )

        since = datetime.now(UTC) - timedelta(days=self.lookback_days)
        history_rows = self.sql.execute(
            f"SELECT * FROM system.query.history "
            f"WHERE start_time >= TIMESTAMP '{since.isoformat()}' "
            f"AND (compute.warehouse_id = '{self.warehouse_id}' "
            f"     OR client_application LIKE '%Power BI%')"
        )
        history = [self._history_row(r) for r in history_rows]

        events_rows = self.sql.execute(
            f"SELECT * FROM system.compute.warehouse_events "
            f"WHERE event_time >= TIMESTAMP '{since.isoformat()}' "
            f"AND warehouse_id = '{self.warehouse_id}'"
        )
        events = [
            WarehouseEvent(
                event_time=_parse_dt(r["event_time"]) or datetime.now(UTC),
                warehouse_id=r["warehouse_id"],
                event_type=r["event_type"],
                cluster_count=r.get("cluster_count"),
            )
            for r in events_rows
        ]

        return WarehouseState(
            warehouse_id=self.warehouse_id,
            name=payload.get("name", self.warehouse_id),
            type=wh_type,
            cluster_size=payload.get("cluster_size", "Medium"),
            auto_stop_mins=payload.get("auto_stop_mins"),
            min_clusters=payload.get("min_num_clusters", 1),
            max_clusters=payload.get("max_num_clusters", 1),
            region=region,
            query_history=history,
            events=events,
        )

    @staticmethod
    def _history_row(r: dict[str, Any]) -> QueryHistoryEntry:
        compute = _as_dict(r.get("compute"))
        return QueryHistoryEntry(
            query_id=r["statement_id"],
            warehouse_id=compute.get("warehouse_id") or r.get("warehouse_id"),
            all_purpose_cluster_id=compute.get("cluster_id"),
            client_application=r.get("client_application"),
            statement_type=r.get("statement_type", "SELECT"),
            started_at=_parse_dt(r["start_time"]) or datetime.now(UTC),
            ended_at=_parse_dt(r.get("end_time")),
            execution_time_ms=int(r.get("total_duration_ms") or 0),
            queue_duration_ms=int(r.get("waiting_for_compute_duration_ms") or 0),
            compute_used_mb=r.get("compute_used_mb"),
            rows_produced=r.get("produced_rows"),
            spilled_to_disk=int(r.get("spilled_local_bytes") or 0) > 0,
            referenced_tables=[str(x) for x in _as_list(r.get("read_partitions"))],
        )

    def _catalog_state(self, wh: WarehouseState) -> CatalogState:
        clauses: list[str] = []
        for c in self.catalogs:
            parts = c.split(".", 1)
            cat = parts[0]
            schema = parts[1] if len(parts) > 1 else None
            if schema:
                clauses.append(f"(table_catalog = '{cat}' AND table_schema = '{schema}')")
            else:
                clauses.append(f"(table_catalog = '{cat}')")
        catalog_filter = " OR ".join(clauses)
        tbl_rows = self.sql.execute(
            f"SELECT * FROM system.information_schema.tables WHERE {catalog_filter}"
        )
        col_rows = self.sql.execute(
            f"SELECT * FROM system.information_schema.columns WHERE {catalog_filter}"
        )
        cons_rows = self.sql.execute(
            f"SELECT * FROM system.information_schema.table_constraints WHERE {catalog_filter}"
        )

        cols_by_table: dict[str, list[ColumnMetadata]] = {}
        for col in col_rows:
            full = f"{col['table_catalog']}.{col['table_schema']}.{col['table_name']}"
            cols_by_table.setdefault(full, []).append(
                ColumnMetadata(
                    name=col["column_name"],
                    data_type=col["full_data_type"],
                    is_nullable=col["is_nullable"] == "YES",
                    max_length_observed=None,
                )
            )

        cons_by_table: dict[str, dict[str, Any]] = {}
        for con in cons_rows:
            full = f"{con['table_catalog']}.{con['table_schema']}.{con['table_name']}"
            cons_by_table.setdefault(full, {"pk": None, "rely": False, "fks": []})
            if con["constraint_type"] == "PRIMARY KEY":
                cons_by_table[full]["pk"] = list(con.get("key_columns", []))
                cons_by_table[full]["rely"] = bool(con.get("rely"))
            elif con["constraint_type"] == "FOREIGN KEY":
                cons_by_table[full]["fks"].append(
                    ForeignKey(
                        from_columns=list(con.get("key_columns", [])),
                        to_table=con.get("referenced_table", ""),
                        to_columns=list(con.get("referenced_columns", [])),
                        rely=bool(con.get("rely")),
                    )
                )

        tables: list[TableMetadata] = []
        for t in tbl_rows:
            full = f"{t['table_catalog']}.{t['table_schema']}.{t['table_name']}"
            ext = self.sql.describe_extended(full)
            cluster_kind = ext.get("clustering_kind", "none")
            tables.append(
                TableMetadata(
                    full_name=full,
                    layer=_layer_for(t["table_schema"]),
                    columns=cols_by_table.get(full, []),
                    primary_key=cons_by_table.get(full, {}).get("pk"),
                    foreign_keys=cons_by_table.get(full, {}).get("fks", []),
                    rely=cons_by_table.get(full, {}).get("rely", False),
                    clustering=ClusteringInfo(
                        kind=cluster_kind,
                        columns=list(ext.get("clustering_columns", [])),
                    ),
                    last_optimize_at=_parse_dt(ext.get("last_optimize_at")),
                    last_vacuum_at=_parse_dt(ext.get("last_vacuum_at")),
                    predictive_optimization=bool(ext.get("predictive_optimization")),
                    has_column_stats=bool(ext.get("has_column_stats")),
                    is_materialized_view=bool(ext.get("is_materialized_view")),
                    size_bytes=ext.get("size_bytes"),
                )
            )

        referenced = sorted(
            {
                t
                for q in wh.query_history
                for t in (q.referenced_tables or [])
                if t and any(t.startswith(c + ".") for c in self.catalogs)
            }
        )
        return CatalogState(tables=tables, referenced_by_powerbi=referenced)
