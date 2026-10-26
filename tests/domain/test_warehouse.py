from datetime import UTC, datetime, timedelta

import pytest

from powerbi_analyzer.domain.warehouse import (
    QueryHistoryEntry,
    WarehouseEvent,
    WarehouseState,
    is_powerbi_client,
)


def test_warehouse_state_minimal():
    ws = WarehouseState(
        warehouse_id="abc",
        name="bi-prod",
        type="serverless",
        cluster_size="Medium",
        auto_stop_mins=10,
        min_clusters=1,
        max_clusters=4,
        region="us-east-1",
        query_history=[],
        events=[],
    )
    assert ws.type == "serverless"


def test_query_history_entry_round_trip():
    now = datetime.now(UTC)
    e = QueryHistoryEntry(
        query_id="q1",
        warehouse_id="abc",
        client_application="Power BI Desktop",
        statement_type="SELECT",
        started_at=now,
        ended_at=now + timedelta(seconds=2),
        execution_time_ms=2000,
        queue_duration_ms=10,
        compute_used_mb=128,
        rows_produced=42,
        spilled_to_disk=False,
        all_purpose_cluster_id=None,
    )
    assert e.execution_time_ms == 2000


def test_warehouse_event():
    e = WarehouseEvent(
        event_time=datetime.now(UTC),
        warehouse_id="abc",
        event_type="SCALED_UP",
        cluster_count=3,
    )
    assert e.cluster_count == 3


@pytest.mark.parametrize(
    "app",
    ["Power BI", "Power BI Desktop", "Power BI Service", "PowerBI", "power bi", "POWER-BI"],
)
def test_is_powerbi_client_matches_known_variants(app: str) -> None:
    assert is_powerbi_client(app)


@pytest.mark.parametrize("app", [None, "", "Tableau", "DBeaver", "Databricks SQL Editor", "dbt"])
def test_is_powerbi_client_rejects_other_clients(app: str | None) -> None:
    assert not is_powerbi_client(app)
