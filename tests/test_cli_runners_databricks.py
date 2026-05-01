# tests/test_cli_runners_databricks.py
from pathlib import Path
from unittest.mock import patch

from tests.collectors.test_databricks import StubSqlExecutor, StubWorkspaceClient


def test_run_databricks_writes_markdown_report(tmp_path: Path):
    from powerbi_analyzer import cli_runners

    out = tmp_path / "report.md"
    with patch.object(
        cli_runners,
        "_make_databricks_clients",
        return_value=(StubSqlExecutor(), StubWorkspaceClient()),
    ):
        rc = cli_runners.run_databricks(
            profile="DEFAULT",
            warehouse_id="wh-test-001",
            catalogs=["main.gold", "main.staging"],
            lookback_days=30,
            out=out,
            formats="markdown",
            ignore=set(),
            fail_on="none",
        )
    assert rc == 0
    md = out.read_text()
    assert "SS-001" in md
    assert "SS-002" in md
    assert "SS-003" in md
    assert "Auto stop" in md
