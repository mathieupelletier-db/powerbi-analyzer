"""Tests for WorkspaceCollector using injected stub clients."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from powerbi_analyzer.collectors.workspace import (
    HttpXmlaRestClient,
    PowerBiRestClient,
    WorkspaceCollector,
    XmlaRestClient,
    _raise_with_body,
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


def _resp(status: int, *, json_body: Any = None, text: str = "", reason: str = "") -> MagicMock:
    r = MagicMock(spec=requests.Response)
    r.status_code = status
    r.ok = 200 <= status < 400
    r.reason = reason or ("OK" if r.ok else "Bad Request")
    r.text = text
    if json_body is None:
        r.json.side_effect = ValueError("no json")
    else:
        r.json.return_value = json_body
    return r


def test_raise_with_body_passthrough_on_success() -> None:
    _raise_with_body(_resp(200, json_body={}), "GET /x")  # no exception


def test_raise_with_body_surfaces_powerbi_error_code() -> None:
    r = _resp(
        400,
        json_body={
            "error": {
                "code": "DatasetExecuteQueriesError",
                "message": "Query execution is not allowed for this dataset.",
            }
        },
    )
    with pytest.raises(requests.HTTPError) as exc:
        _raise_with_body(r, "POST executeQueries")
    msg = str(exc.value)
    assert "400" in msg
    assert "POST executeQueries" in msg
    assert "DatasetExecuteQueriesError" in msg
    assert "Query execution is not allowed" in msg


def _ok_resp(rows: list[dict[str, Any]]) -> MagicMock:
    r = MagicMock(spec=requests.Response)
    r.status_code = 200
    r.ok = True
    r.reason = "OK"
    r.json.return_value = {"results": [{"tables": [{"rows": rows}]}]}
    return r


def _fabric_default_400() -> MagicMock:
    r = MagicMock(spec=requests.Response)
    r.status_code = 400
    r.ok = False
    r.reason = "Bad Request"
    r.text = ""
    r.json.return_value = {"error": {"code": "DatasetExecuteQueriesError", "message": ""}}
    return r


def test_xmla_strips_bracketed_keys() -> None:
    """Power BI returns column names wrapped in brackets — unwrap them."""
    client = HttpXmlaRestClient(token="t")
    with patch(
        "powerbi_analyzer.collectors.workspace.requests.post",
        return_value=_ok_resp([{"[Name]": "Fact", "[StorageMode]": "Import"}]),
    ):
        rows = client.info_tables("ws", "ds")
    assert rows == [{"Name": "Fact", "StorageMode": "Import"}]


def test_xmla_falls_back_to_info_view_on_dataset_error() -> None:
    """Fabric default semantic models reject INFO.TABLES() — retry with INFO.VIEW.TABLES()."""
    client = HttpXmlaRestClient(token="t")
    classic_fail = _fabric_default_400()
    view_ok = _ok_resp([{"[Name]": "Fact", "[StorageMode]": "Import", "[IsHidden]": False}])

    with patch(
        "powerbi_analyzer.collectors.workspace.requests.post",
        side_effect=[classic_fail, view_ok],
    ) as post:
        rows = client.info_tables("ws", "ds")

    assert post.call_count == 2
    classic_query = post.call_args_list[0].kwargs["json"]["queries"][0]["query"]
    view_query = post.call_args_list[1].kwargs["json"]["queries"][0]["query"]
    assert "INFO.TABLES()" in classic_query
    assert "INFO.VIEW.TABLES()" in view_query
    assert rows[0]["Name"] == "Fact"


def test_xmla_view_relationships_normalizes_cardinality_codes() -> None:
    """INFO.VIEW.RELATIONSHIPS uses string cardinality; bridge to classic int code."""
    client = HttpXmlaRestClient(token="t")
    view_row = {
        "[FromTable]": "flights",
        "[FromColumn]": "Origin",
        "[ToTable]": "airports",
        "[ToColumn]": "IATA",
        "[FromCardinality]": "Many",
        "[ToCardinality]": "One",
        "[CrossFilteringBehavior]": "OneDirection",
        "[IsActive]": True,
        "[RelyOnReferentialIntegrity]": True,
    }
    with patch(
        "powerbi_analyzer.collectors.workspace.requests.post",
        side_effect=[_fabric_default_400(), _ok_resp([view_row])],
    ):
        rows = client.info_relationships("ws", "ds")

    assert rows[0]["Cardinality"] == 3  # Many→One = many-to-one
    assert rows[0]["CrossFilteringBehavior"] == 1  # OneDirection = single
    assert rows[0]["FromTable"] == "flights"


def test_xmla_view_measures_aliases_table_to_tablename() -> None:
    """INFO.VIEW.MEASURES uses 'Table' but the collector reads 'TableName'."""
    client = HttpXmlaRestClient(token="t")
    view_row = {"[Name]": "Total Sales", "[Table]": "Fact", "[DataType]": "Number"}
    with patch(
        "powerbi_analyzer.collectors.workspace.requests.post",
        side_effect=[_fabric_default_400(), _ok_resp([view_row])],
    ):
        rows = client.info_measures("ws", "ds")
    assert rows[0]["TableName"] == "Fact"
    assert rows[0]["Name"] == "Total Sales"


def test_xmla_does_not_fall_back_on_unrelated_400() -> None:
    """Only DatasetExecuteQueriesError triggers the VIEW fallback — others propagate."""
    client = HttpXmlaRestClient(token="t")
    other_400 = MagicMock(spec=requests.Response)
    other_400.status_code = 400
    other_400.ok = False
    other_400.reason = "Bad Request"
    other_400.text = ""
    other_400.json.return_value = {"error": {"code": "InvalidRequest", "message": "bad"}}

    with (
        patch(
            "powerbi_analyzer.collectors.workspace.requests.post", return_value=other_400
        ) as post,
        pytest.raises(requests.HTTPError),
    ):
        client.info_tables("ws", "ds")
    assert post.call_count == 1  # no fallback attempted


def test_raise_with_body_falls_back_to_text_when_not_json() -> None:
    r = _resp(403, text="Forbidden — caller has no Build permission.")
    with pytest.raises(requests.HTTPError) as exc:
        _raise_with_body(r, "POST executeQueries")
    assert "Forbidden" in str(exc.value)


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
