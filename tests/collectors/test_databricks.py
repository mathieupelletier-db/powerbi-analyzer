# tests/collectors/test_databricks.py
import json
from pathlib import Path

from powerbi_analyzer.collectors.databricks import DatabricksCollector, SqlExecutor

FIXTURES = Path(__file__).parent.parent / "fixtures" / "databricks" / "system_tables"


class StubSqlExecutor(SqlExecutor):
    def __init__(self):
        self._fixtures = {p.stem: json.loads(p.read_text()) for p in FIXTURES.glob("*.json")}

    def execute(self, query: str) -> list[dict]:
        if "system.query.history" in query:
            return self._fixtures["query_history"]
        if "system.compute.warehouse_events" in query:
            return self._fixtures["warehouse_events"]
        if "information_schema.tables" in query:
            return self._fixtures["info_schema_tables"]
        if "information_schema.columns" in query:
            return self._fixtures["info_schema_columns"]
        if "information_schema.table_constraints" in query:
            return self._fixtures["info_schema_constraints"]
        raise AssertionError(f"unexpected query: {query}")

    def describe_extended(self, table: str) -> dict:
        return self._fixtures["describe_extended"][table]


class StubWorkspaceClient:
    def __init__(self):
        self._wh = json.loads((FIXTURES / "warehouse_get.json").read_text())

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
    assert len(wh.query_history) == 2
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
    assert fact.rely is True
    assert fact.clustering.kind == "liquid"
    assert fact.predictive_optimization is True
    staging = next(t for t in cat.tables if t.full_name == "main.staging.orders")
    assert staging.layer == "unknown"
    assert staging.clustering.kind == "none"


def test_referenced_by_powerbi_filtered_from_query_history():
    c = DatabricksCollector(
        warehouse_id="wh-test-001",
        catalogs=["main.gold"],
        lookback_days=30,
        sql=StubSqlExecutor(),
        ws=StubWorkspaceClient(),
    )
    _, cat = c.collect()
    # No referenced_tables in fixture rows; expect empty list rather than crash
    assert cat.referenced_by_powerbi == []
