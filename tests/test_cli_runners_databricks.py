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


def test_run_databricks_formats_html_picks_html_suffix(tmp_path: Path, monkeypatch):
    """Regression: --formats html with no --out must produce a .html file
    and write actual HTML, not markdown with a .md extension."""
    from powerbi_analyzer import cli_runners

    monkeypatch.chdir(tmp_path)
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
            out=None,
            formats="html",
            ignore=set(),
            fail_on="none",
        )
    assert rc == 0
    html_files = list(tmp_path.glob("pba-audit-*.html"))
    md_files = list(tmp_path.glob("pba-audit-*.md"))
    assert len(html_files) == 1, f"expected 1 .html file, got {html_files}"
    assert md_files == [], f"should not have written markdown, got {md_files}"
    body = html_files[0].read_text()
    assert body.lstrip().startswith("<!DOCTYPE html") or "<html" in body[:200].lower()
