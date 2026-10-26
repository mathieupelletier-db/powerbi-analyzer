# tests/collectors/test_databricks.py
import json
from pathlib import Path

from powerbi_analyzer.collectors.databricks import (
    POWERBI_CLIENT_SQL,
    DatabricksCollector,
    SqlExecutor,
    _as_dict,
    _as_list,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "databricks" / "system_tables"


class StubSqlExecutor(SqlExecutor):
    def __init__(self, *, lineage_error: Exception | None = None):
        self._fixtures = {p.stem: json.loads(p.read_text()) for p in FIXTURES.glob("*.json")}
        self._lineage_error = lineage_error
        self.queries: list[str] = []

    def execute(self, query: str) -> list[dict]:
        self.queries.append(query)
        # Checked first: the lineage query embeds a system.query.history subquery.
        if "system.access.table_lineage" in query:
            if self._lineage_error:
                raise self._lineage_error
            return self._fixtures["table_lineage"]
        if "system.query.history" in query:
            return self._fixtures["query_history"]
        if "system.compute.warehouse_events" in query:
            return self._fixtures["warehouse_events"]
        if "information_schema.tables" in query:
            return self._fixtures["info_schema_tables"]
        if "information_schema.columns" in query:
            return self._fixtures["info_schema_columns"]
        if "information_schema.key_column_usage" in query:
            return self._fixtures["info_schema_key_column_usage"]
        if "information_schema.table_constraints" in query:
            return self._fixtures["info_schema_constraints"]
        raise AssertionError(f"unexpected query: {query}")

    def describe_extended(self, table: str) -> dict:
        return self._fixtures["describe_extended"][table]


class StubWorkspaceClient:
    def __init__(self, *, constraints_error: Exception | None = None):
        self._wh = json.loads((FIXTURES / "warehouse_get.json").read_text())
        self._constraints = json.loads((FIXTURES / "uc_table_constraints.json").read_text())
        self._constraints_error = constraints_error
        self.constraint_calls: list[str] = []

    def table_constraints(self, full_name: str) -> list[dict]:
        self.constraint_calls.append(full_name)
        if self._constraints_error:
            raise self._constraints_error
        return self._constraints.get(full_name, [])

    def get_warehouse(self, warehouse_id: str) -> dict:
        return self._wh

    def workspace_region(self) -> str:
        return "us-east-1"


def test_collect_returns_warehouse_state_and_catalog_state():
    c = DatabricksCollector(
        warehouse_id="wh-test-001",
        catalogs=["main.gold", "main.staging"],
        lookback_days=30,
        sql=StubSqlExecutor(),
        ws=StubWorkspaceClient(),
    )
    wh, _cat = c.collect()
    assert wh.warehouse_id == "wh-test-001"
    assert wh.type == "pro"
    assert wh.region == "us-east-1"
    assert wh.auto_stop_mins == 0
    assert len(wh.query_history) == 3
    assert wh.query_history[1].all_purpose_cluster_id == "cluster-XYZ"
    assert any(e.event_type == "SCALED_UP" for e in wh.events)


def test_catalog_state_groups_tables_with_metadata():
    c = DatabricksCollector(
        warehouse_id="wh-test-001",
        catalogs=["main.gold", "main.staging"],
        lookback_days=30,
        sql=StubSqlExecutor(),
        ws=StubWorkspaceClient(),
    )
    _, cat = c.collect()
    fact = next(t for t in cat.tables if t.full_name == "main.gold.fact_sales")
    assert fact.layer == "gold"
    # PK columns + RELY come from the UC Tables API (information_schema has no RELY).
    assert fact.primary_key == ["id", "region_id"]
    assert fact.rely is True
    assert [(fk.to_table, fk.rely) for fk in fact.foreign_keys] == [
        ("main.gold.dim_customer", False)
    ]


def test_tables_api_only_called_for_tables_with_constraints():
    ws = StubWorkspaceClient()
    DatabricksCollector(
        warehouse_id="wh-test-001",
        catalogs=["main.gold", "main.staging"],
        lookback_days=30,
        sql=StubSqlExecutor(),
        ws=ws,
    ).collect()
    assert ws.constraint_calls == ["main.gold.fact_sales"]


def test_tables_api_failure_falls_back_to_information_schema_with_unknown_rely():
    _, cat = DatabricksCollector(
        warehouse_id="wh-test-001",
        catalogs=["main.gold", "main.staging"],
        lookback_days=30,
        sql=StubSqlExecutor(),
        ws=StubWorkspaceClient(constraints_error=PermissionError("denied")),
    ).collect()
    fact = next(t for t in cat.tables if t.full_name == "main.gold.fact_sales")
    assert fact.primary_key == ["id", "region_id"]
    assert fact.rely is None
    assert fact.clustering.kind == "liquid"
    assert fact.predictive_optimization is True
    staging = next(t for t in cat.tables if t.full_name == "main.staging.orders")
    assert staging.layer == "unknown"
    assert staging.clustering.kind == "none"


def _collector(sql: StubSqlExecutor, catalogs: list[str] | None = None) -> DatabricksCollector:
    return DatabricksCollector(
        warehouse_id="wh-test-001",
        catalogs=catalogs or ["main.gold", "main.staging"],
        lookback_days=30,
        sql=sql,
        ws=StubWorkspaceClient(),
    )


def test_referenced_tables_come_from_table_lineage_not_read_partitions():
    wh, _ = _collector(StubSqlExecutor()).collect()
    by_id = {q.query_id: q for q in wh.query_history}
    assert by_id["q1"].referenced_tables == ["main.gold.fact_sales", "other.sales.dim_region"]
    assert by_id["q2"].referenced_tables == []
    assert wh.table_lineage_error is None


def test_referenced_by_powerbi_only_counts_powerbi_queries_in_scanned_catalogs():
    _, cat = _collector(StubSqlExecutor()).collect()
    # q3 (dbt) reads main.staging.orders; other.sales is outside the scanned catalogs.
    assert cat.referenced_by_powerbi == ["main.gold.fact_sales"]


def test_lineage_query_is_scoped_to_powerbi_statements_in_window():
    sql = StubSqlExecutor()
    _collector(sql).collect()
    lineage = next(q for q in sql.queries if "system.access.table_lineage" in q)
    assert "statement_id IN (SELECT statement_id FROM system.query.history" in lineage
    assert POWERBI_CLIENT_SQL in lineage
    assert "event_time >= TIMESTAMP" in lineage


def test_history_query_matches_powerbi_client_case_and_space_insensitively():
    sql = StubSqlExecutor()
    _collector(sql).collect()
    history = next(q for q in sql.queries if q.startswith("SELECT * FROM system.query.history"))
    assert POWERBI_CLIENT_SQL in history
    assert "LIKE '%Power BI%'" not in history


def test_lineage_failure_degrades_instead_of_aborting():
    sql = StubSqlExecutor(lineage_error=PermissionError("PERMISSION_DENIED: table_lineage"))
    wh, cat = _collector(sql).collect()
    assert len(wh.query_history) == 3
    assert all(q.referenced_tables == [] for q in wh.query_history)
    assert wh.table_lineage_error == "permission denied"
    assert cat.referenced_by_powerbi == []


def test_lineage_error_never_carries_raw_exception_text():
    sql = StubSqlExecutor(lineage_error=RuntimeError("boom at host=adb-123.cloud SELECT secret"))
    wh, _ = _collector(sql).collect()
    assert wh.table_lineage_error == "query failed (RuntimeError)"


def test_catalog_scope_match_is_case_insensitive():
    _, cat = _collector(StubSqlExecutor(), catalogs=["MAIN.Gold"]).collect()
    assert cat.referenced_by_powerbi == ["main.gold.fact_sales"]


def test_as_dict_handles_dict() -> None:
    assert _as_dict({"warehouse_id": "abc"}) == {"warehouse_id": "abc"}


def test_as_dict_parses_json_string() -> None:
    """Some Databricks SQL connector paths return STRUCT cells as JSON strings."""
    assert _as_dict('{"warehouse_id": "abc", "cluster_id": null}') == {
        "warehouse_id": "abc",
        "cluster_id": None,
    }


def test_as_dict_handles_none_and_garbage() -> None:
    assert _as_dict(None) == {}
    assert _as_dict("not json") == {}
    assert _as_dict(42) == {}


def test_as_list_handles_list_string_none() -> None:
    assert _as_list(["a", "b"]) == ["a", "b"]
    assert _as_list('["x", "y"]') == ["x", "y"]
    assert _as_list(None) == []
    assert _as_list("nope") == []
    assert _as_list(("a", "b")) == ["a", "b"]


def test_as_list_handles_array_like_with_tolist() -> None:
    """Arrow/pandas paths can hand back numpy arrays for ARRAY columns."""

    class FakeNdarray:
        def tolist(self) -> list[str]:
            return ["x"]

    assert _as_list(FakeNdarray()) == ["x"]


def test_history_row_defaults_statement_type_when_null() -> None:
    """system.query.history can return statement_type as SQL NULL (None);
    we must coerce to the default rather than letting pydantic reject it."""
    row = {
        "statement_id": "q1",
        "compute": {"warehouse_id": "wh-1"},
        "client_application": "Power BI Desktop",
        "statement_type": None,
        "start_time": "2026-05-01T00:00:00Z",
    }
    entry = DatabricksCollector._history_row(row)
    assert entry.statement_type == "SELECT"
