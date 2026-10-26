"""Databricks-side collector — warehouse REST + system tables."""

from __future__ import annotations

import json
import logging
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
    is_powerbi_client,
)

log = logging.getLogger(__name__)

# SQL twin of domain.warehouse.is_powerbi_client — keep the two in sync.
POWERBI_CLIENT_SQL = "lower(regexp_replace(client_application, '[^A-Za-z]', '')) LIKE '%powerbi%'"

GOLD_HINTS = {"gold", "serving", "mart", "marts", "presentation"}
SILVER_HINTS = {"silver", "curated"}
BRONZE_HINTS = {"bronze", "raw", "landing"}


class WorkspaceClient(Protocol):
    def get_warehouse(self, warehouse_id: str) -> dict[str, Any]: ...
    def workspace_region(self) -> str: ...
    def table_constraints(self, full_name: str) -> list[dict[str, Any]]: ...


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
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    # numpy arrays (pandas-backed result paths) expose .tolist()
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        result = tolist()
        return result if isinstance(result, list) else []
    return []


def _lineage_error_category(exc: Exception) -> str:
    """Report-safe summary of a lineage failure; raw text can carry SQL or hostnames."""
    text = str(exc).upper()
    if any(k in text for k in ("PERMISSION_DENIED", "INSUFFICIENT_PERMISSIONS", "UNAUTHORIZED")):
        return "permission denied"
    if isinstance(exc, PermissionError):
        return "permission denied"
    if "TABLE_OR_VIEW_NOT_FOUND" in text or "SCHEMA_NOT_FOUND" in text:
        return "system table not enabled"
    return f"query failed ({type(exc).__name__})"


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
            f"     OR {POWERBI_CLIENT_SQL})"
        )
        lineage, lineage_error = self._tables_by_statement(since)
        history = [
            self._history_row(r, lineage.get(str(r["statement_id"]), [])) for r in history_rows
        ]

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
            table_lineage_error=lineage_error,
        )

    def _tables_by_statement(self, since: datetime) -> tuple[dict[str, list[str]], str | None]:
        """Map Power BI statement_id -> source tables via system.access.table_lineage.

        system.query.history has no table list (read_partitions is a count), so
        lineage is the documented join (statement_id is a FK to query history).
        Lineage access is often granted separately; degrade rather than abort.
        """
        try:
            rows = self.sql.execute(
                f"SELECT statement_id, "
                f"to_json(array_sort(collect_set(source_table_full_name))) AS source_tables "
                f"FROM system.access.table_lineage "
                f"WHERE event_time >= TIMESTAMP '{since.isoformat()}' "
                f"AND source_table_full_name IS NOT NULL "
                f"AND statement_id IN (SELECT statement_id FROM system.query.history "
                f"WHERE start_time >= TIMESTAMP '{since.isoformat()}' "
                f"AND {POWERBI_CLIENT_SQL}) "
                f"GROUP BY statement_id"
            )
        except Exception as exc:
            log.warning("system.access.table_lineage unavailable: %s", exc)
            return {}, _lineage_error_category(exc)
        return {
            str(r["statement_id"]): [str(t) for t in _as_list(r.get("source_tables"))] for r in rows
        }, None

    @staticmethod
    def _history_row(r: dict[str, Any], tables: list[str] | None = None) -> QueryHistoryEntry:
        compute = _as_dict(r.get("compute"))
        return QueryHistoryEntry(
            query_id=r["statement_id"],
            warehouse_id=compute.get("warehouse_id") or r.get("warehouse_id"),
            all_purpose_cluster_id=compute.get("cluster_id"),
            client_application=r.get("client_application"),
            statement_type=r.get("statement_type") or "SELECT",
            started_at=_parse_dt(r["start_time"]) or datetime.now(UTC),
            ended_at=_parse_dt(r.get("end_time")),
            execution_time_ms=int(r.get("total_duration_ms") or 0),
            queue_duration_ms=int(r.get("waiting_for_compute_duration_ms") or 0),
            compute_used_mb=r.get("compute_used_mb"),
            rows_produced=r.get("produced_rows"),
            spilled_to_disk=int(r.get("spilled_local_bytes") or 0) > 0,
            referenced_tables=list(tables or []),
        )

    def _uc_constraints(self, full_name: str) -> dict[str, Any] | None:
        """PK/FK incl. RELY from the UC Tables API; None if unavailable.

        information_schema does not expose RELY. The Tables API returns
        `rely: true` when declared and omits the field otherwise.
        """
        try:
            raw = self.ws.table_constraints(full_name)
        except Exception as exc:
            log.warning("tables.get(%s) failed; RELY unknown: %s", full_name, exc)
            return None
        out: dict[str, Any] = {"pk": None, "rely": None, "fks": []}
        for c in raw:
            if pk := c.get("primary_key_constraint"):
                out["pk"] = list(pk.get("child_columns", []))
                out["rely"] = bool(pk.get("rely", False))
            elif fk := c.get("foreign_key_constraint"):
                out["fks"].append(
                    ForeignKey(
                        from_columns=list(fk.get("child_columns", [])),
                        to_table=fk.get("parent_table", ""),
                        to_columns=list(fk.get("parent_columns", [])),
                        rely=bool(fk.get("rely", False)),
                    )
                )
        return out

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
        # table_constraints has no column list; key columns live in key_column_usage.
        kcu_rows = self.sql.execute(
            f"SELECT * FROM system.information_schema.key_column_usage WHERE {catalog_filter}"
        )
        key_columns: dict[tuple[str, str], list[tuple[int, str]]] = {}
        for k in kcu_rows:
            full = f"{k['table_catalog']}.{k['table_schema']}.{k['table_name']}"
            key_columns.setdefault((full, k["constraint_name"]), []).append(
                (int(k.get("ordinal_position") or 0), k["column_name"])
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
            cons_by_table.setdefault(full, {"pk": None, "rely": None, "fks": []})
            if con["constraint_type"] == "PRIMARY KEY":
                cols = sorted(key_columns.get((full, con.get("constraint_name", "")), []))
                cons_by_table[full]["pk"] = [c for _, c in cols] or list(con.get("key_columns", []))
                # RELY is not in information_schema; resolved from the Tables API below.
                cons_by_table[full]["rely"] = con.get("rely")
            elif con["constraint_type"] == "FOREIGN KEY":
                cons_by_table[full]["fks"].append(
                    ForeignKey(
                        from_columns=list(con.get("key_columns", [])),
                        to_table=con.get("referenced_table", ""),
                        to_columns=list(con.get("referenced_columns", [])),
                        rely=con.get("rely"),
                    )
                )
        for full in cons_by_table:
            uc = self._uc_constraints(full)
            if uc is not None:
                cons_by_table[full] = uc

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
                    rely=cons_by_table.get(full, {}).get("rely"),
                    clustering=ClusteringInfo(
                        kind=cluster_kind,
                        columns=list(ext.get("clustering_columns", [])),
                    ),
                    last_optimize_at=_parse_dt(ext.get("last_optimize_at")),
                    last_vacuum_at=_parse_dt(ext.get("last_vacuum_at")),
                    predictive_optimization=bool(ext.get("predictive_optimization")),
                    has_column_stats=ext.get("has_column_stats"),
                    is_materialized_view=bool(ext.get("is_materialized_view")),
                    size_bytes=ext.get("size_bytes"),
                )
            )

        # UC identifiers are case-insensitive; lineage reports them lowercased.
        scopes = [c.lower() + "." for c in self.catalogs]
        referenced = sorted(
            {
                t.lower()
                for q in wh.query_history
                if is_powerbi_client(q.client_application)
                for t in (q.referenced_tables or [])
                if t and t.lower().startswith(tuple(scopes))
            }
        )
        return CatalogState(tables=tables, referenced_by_powerbi=referenced)
