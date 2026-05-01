"""Tests for WorkspaceCollector using injected stub clients."""
from __future__ import annotations

from typing import Any

import pytest

from powerbi_analyzer.collectors.workspace import (
    PowerBiRestClient,
    WorkspaceCollector,
    XmlaRestClient,
)


class StubRest(PowerBiRestClient):
    def __init__(self) -> None:
        pass

    def list_datasets(self, ws: str) -> list[dict[str, Any]]:
        return [{"id": "d1", "name": "Sales", "configuredBy": "x"}]

    def get_workspace(self, ws: str) -> dict[str, Any]:
        return {"id": ws, "name": "ws", "capacityRegion": "eastus"}

    def get_capacity_settings(self, ws: str) -> dict[str, Any]:
        return {"sso": True, "automaticPublishing": False, "publishToService": True}

    def get_parallelism(self, ws: str, ds: str) -> dict[str, Any]:
        return {
            "maxConnectionsPerDataSource": 10,
            "maxConcurrentJobs": 6,
            "maxParallelismPerQuery": 1,
            "maxSimultaneousEvaluations": 6,
        }

    def list_gateways(self) -> list[dict[str, Any]]:
        return []


class StubXmla(XmlaRestClient):
    def __init__(self) -> None:
        pass

    def info_tables(self, ws: str, ds: str) -> list[dict[str, Any]]:
        return [{"Name": "Fact", "RowCount": 1000, "StorageMode": "DirectQuery"}]

    def info_columns(self, ws: str, ds: str) -> list[dict[str, Any]]:
        return [
            {"Table": "Fact", "Name": "id", "DataType": "int64", "IsNullable": False, "IsKey": True}
        ]

    def info_relationships(self, ws: str, ds: str) -> list[dict[str, Any]]:
        return []

    def info_measures(self, ws: str, ds: str) -> list[dict[str, Any]]:
        return []


def test_collect_returns_model_and_config() -> None:
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=StubXmla(),
    )
    sm, cfg = c.collect()
    assert sm.source == "workspace"
    assert cfg.workspace_id == "ws-1"
    assert cfg.capacity_region == "eastus"
    assert cfg.sso_enabled is True
    assert sm.tables[0].name == "Fact"


def test_collect_table_row_count() -> None:
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=StubXmla(),
    )
    sm, _ = c.collect()
    assert sm.tables[0].row_count == 1000


def test_collect_column_mapped() -> None:
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=StubXmla(),
    )
    sm, _ = c.collect()
    col = sm.tables[0].columns[0]
    assert col.name == "id"
    assert col.is_key is True
    assert col.is_nullable is False


def test_collect_no_relationships() -> None:
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=StubXmla(),
    )
    sm, _ = c.collect()
    assert sm.relationships == []


def test_collect_no_measures() -> None:
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=StubXmla(),
    )
    sm, _ = c.collect()
    assert sm.measures == []


def test_collect_parallelism_config() -> None:
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=StubXmla(),
    )
    _, cfg = c.collect()
    assert cfg.parallelism.max_connections_per_data_source == 10
    assert cfg.parallelism.max_concurrent_jobs == 6
    assert cfg.parallelism.max_parallelism_per_query == 1
    assert cfg.parallelism.max_simultaneous_evaluations == 6


def test_collect_publish_flags() -> None:
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=StubXmla(),
    )
    _, cfg = c.collect()
    assert cfg.publish_to_pbi_service is True
    assert cfg.automatic_publishing is False


def test_collect_no_gateway() -> None:
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=StubXmla(),
    )
    _, cfg = c.collect()
    assert cfg.gateway is None


def test_collect_explicit_dataset_ids() -> None:
    """When dataset_ids is provided explicitly, collector uses that list."""
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=["d1"],
        rest=StubRest(),
        xmla=StubXmla(),
    )
    sm, cfg = c.collect()
    assert sm.source == "workspace"
    assert cfg.workspace_id == "ws-1"


def test_collect_model_name_from_dataset() -> None:
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=StubXmla(),
    )
    sm, _ = c.collect()
    assert sm.name == "Sales"


def test_collect_no_datasets_raises() -> None:
    class EmptyRest(StubRest):
        def list_datasets(self, ws: str) -> list[dict[str, Any]]:
            return []

    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=EmptyRest(),
        xmla=StubXmla(),
    )
    from powerbi_analyzer.collectors.base import CollectorError

    with pytest.raises(CollectorError):
        c.collect()


def test_collect_gateway_config() -> None:
    class GatewayRest(StubRest):
        def list_gateways(self) -> list[dict[str, Any]]:
            return [{"name": "my-gw", "numberOfMachines": 3}]

    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=GatewayRest(),
        xmla=StubXmla(),
    )
    _, cfg = c.collect()
    assert cfg.gateway is not None
    assert cfg.gateway.name == "my-gw"
    assert cfg.gateway.cluster_size == 3


def test_collect_with_relationships() -> None:
    class RelXmla(StubXmla):
        def info_relationships(self, ws: str, ds: str) -> list[dict[str, Any]]:
            return [
                {
                    "FromTable": "Fact",
                    "FromColumn": "dim_id",
                    "ToTable": "Dim",
                    "ToColumn": "id",
                    "Cardinality": 2,
                    "CrossFilteringBehavior": 1,
                    "IsActive": True,
                    "RelyOnReferentialIntegrity": False,
                }
            ]

    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=RelXmla(),
    )
    sm, _ = c.collect()
    assert len(sm.relationships) == 1
    rel = sm.relationships[0]
    assert rel.from_table == "Fact"
    assert rel.to_table == "Dim"
    assert rel.cardinality == "one-to-many"
    assert rel.cross_filter == "single"


def test_collect_with_measures() -> None:
    class MeasXmla(StubXmla):
        def info_measures(self, ws: str, ds: str) -> list[dict[str, Any]]:
            return [
                {
                    "Name": "Total Sales",
                    "TableName": "Fact",
                    "Expression": "SUM(Fact[Amount])",
                    "FormatString": "#,##0",
                }
            ]

    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=MeasXmla(),
    )
    sm, _ = c.collect()
    assert len(sm.measures) == 1
    m = sm.measures[0]
    assert m.name == "Total Sales"
    assert m.table == "Fact"
    assert m.format_string == "#,##0"


def test_collect_storage_mode_directquery() -> None:
    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=StubXmla(),
    )
    sm, _ = c.collect()
    from powerbi_analyzer.domain.semantic_model import StorageMode

    assert sm.tables[0].storage_mode == StorageMode.DIRECT_QUERY


def test_collect_composite_model_detection() -> None:
    """is_composite=True when multiple distinct storage modes present."""

    class MixedXmla(StubXmla):
        def info_tables(self, ws: str, ds: str) -> list[dict[str, Any]]:
            return [
                {"Name": "Fact", "RowCount": 1000, "StorageMode": "DirectQuery"},
                {"Name": "Dim", "RowCount": 50, "StorageMode": "import"},
            ]

    c = WorkspaceCollector(
        workspace_id="ws-1",
        dataset_ids=None,
        rest=StubRest(),
        xmla=MixedXmla(),
    )
    sm, _ = c.collect()
    assert sm.is_composite is True
