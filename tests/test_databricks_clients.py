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
        assert kwargs["access_token"] == "tok"
        assert rows == [{"col": "v"}]
