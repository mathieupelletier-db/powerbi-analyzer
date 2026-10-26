"""Tests for SdkSqlExecutor http_path resolution and lazy connect."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _patch_workspace_client(host: str = "https://example.cloud.databricks.com") -> MagicMock:
    """Build a mocked databricks WorkspaceClient with usable cfg."""
    wc = MagicMock()
    wc.config.host = host
    wc.config.token = "tok"
    return wc


def test_http_path_derived_from_warehouse_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PBA_HTTP_PATH", raising=False)
    from powerbi_analyzer import databricks_clients

    with patch.object(
        databricks_clients, "WorkspaceClient", return_value=_patch_workspace_client()
    ):
        ex = databricks_clients.SdkSqlExecutor(profile="DEFAULT", warehouse_id="abc123")
    assert ex._http_path == "/sql/1.0/warehouses/abc123"


def test_explicit_pba_http_path_overrides_warehouse_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PBA_HTTP_PATH", "/sql/1.0/warehouses/manual-override")
    from powerbi_analyzer import databricks_clients

    with patch.object(
        databricks_clients, "WorkspaceClient", return_value=_patch_workspace_client()
    ):
        ex = databricks_clients.SdkSqlExecutor(profile="DEFAULT", warehouse_id="abc123")
    assert ex._http_path == "/sql/1.0/warehouses/manual-override"


def test_missing_http_path_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PBA_HTTP_PATH", raising=False)
    from powerbi_analyzer import databricks_clients

    with (
        patch.object(databricks_clients, "WorkspaceClient", return_value=_patch_workspace_client()),
        pytest.raises(ValueError, match="--warehouse-id"),
    ):
        databricks_clients.SdkSqlExecutor(profile="DEFAULT")


def test_connection_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Constructor should not call dbsql.connect — only the first execute() does."""
    monkeypatch.delenv("PBA_HTTP_PATH", raising=False)
    from powerbi_analyzer import databricks_clients

    with (
        patch.object(databricks_clients, "WorkspaceClient", return_value=_patch_workspace_client()),
        patch.object(databricks_clients, "dbsql") as dbsql,
    ):
        ex = databricks_clients.SdkSqlExecutor(profile="DEFAULT", warehouse_id="abc")
        assert dbsql.connect.call_count == 0  # not yet
        # Trigger lazy connect
        cur = MagicMock()
        cur.description = [("col",)]
        cur.fetchall.return_value = [("v",)]
        ctx = MagicMock()
        ctx.__enter__.return_value = cur
        ctx.__exit__.return_value = False
        dbsql.connect.return_value.cursor.return_value = ctx

        rows = ex.execute("SELECT 1")
        assert dbsql.connect.call_count == 1
        kwargs = dbsql.connect.call_args.kwargs
        assert kwargs["server_hostname"] == "example.cloud.databricks.com"
        assert kwargs["http_path"] == "/sql/1.0/warehouses/abc"
        # Auth is delegated to the SDK config so OAuth / CLI profiles work, not just PATs.
        assert "access_token" not in kwargs
        assert kwargs["credentials_provider"]() is ex._wc.config.authenticate
        assert rows == [{"col": "v"}]


def test_connect_works_for_oauth_profile_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """databricks-cli / OAuth profiles have no static token; must not fall back to browser U2M."""
    monkeypatch.delenv("PBA_HTTP_PATH", raising=False)
    from powerbi_analyzer import databricks_clients

    wc = _patch_workspace_client()
    wc.config.token = None
    with (
        patch.object(databricks_clients, "WorkspaceClient", return_value=wc),
        patch.object(databricks_clients, "dbsql") as dbsql,
    ):
        databricks_clients.SdkSqlExecutor(profile="DEFAULT", warehouse_id="abc")._connection()
    kwargs = dbsql.connect.call_args.kwargs
    assert "access_token" not in kwargs
    assert kwargs["credentials_provider"]() is wc.config.authenticate


def test_describe_extended_parses_real_predictive_optimization_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Row shape captured from DESCRIBE TABLE EXTENDED on a live UC managed table."""
    monkeypatch.delenv("PBA_HTTP_PATH", raising=False)
    from powerbi_analyzer import databricks_clients

    rows = [
        {"col_name": "c_custkey", "data_type": "bigint", "comment": None},
        {"col_name": "Statistics", "data_type": "8725553 bytes, 150000 rows", "comment": ""},
        {"col_name": "Type", "data_type": "MANAGED", "comment": ""},
        {
            "col_name": "Predictive Optimization",
            "data_type": "ENABLE (inherited from METASTORE metastore_x)",
            "comment": "",
        },
    ]
    with patch.object(
        databricks_clients, "WorkspaceClient", return_value=_patch_workspace_client()
    ):
        ex = databricks_clients.SdkSqlExecutor(profile="DEFAULT", warehouse_id="abc")
    with patch.object(ex, "execute", side_effect=[rows, []]):
        out = ex.describe_extended("c.s.t")
    assert out["predictive_optimization"] is True
    # Column-level statistics are not collected; must be unknown, not False.
    assert out["has_column_stats"] is None


@pytest.mark.parametrize("value", ["DISABLE", "DISABLE (inherited from CATALOG c)"])
def test_describe_extended_predictive_optimization_disabled(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.delenv("PBA_HTTP_PATH", raising=False)
    from powerbi_analyzer import databricks_clients

    rows = [{"col_name": "Predictive Optimization", "data_type": value, "comment": ""}]
    with patch.object(
        databricks_clients, "WorkspaceClient", return_value=_patch_workspace_client()
    ):
        ex = databricks_clients.SdkSqlExecutor(profile="DEFAULT", warehouse_id="abc")
    with patch.object(ex, "execute", side_effect=[rows, []]):
        assert ex.describe_extended("c.s.t")["predictive_optimization"] is False


def test_table_constraints_reads_uc_tables_api() -> None:
    from powerbi_analyzer import databricks_clients

    wc = MagicMock()
    wc.tables.get.return_value.as_dict.return_value = {
        "table_constraints": [{"primary_key_constraint": {"child_columns": ["id"], "rely": True}}]
    }
    with patch.object(databricks_clients, "WorkspaceClient", return_value=wc):
        client = databricks_clients.SdkWorkspaceClient(profile="DEFAULT")
    assert client.table_constraints("c.s.t") == [
        {"primary_key_constraint": {"child_columns": ["id"], "rely": True}}
    ]
    wc.tables.get.assert_called_once_with("c.s.t")
