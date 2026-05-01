"""CLI command implementations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from powerbi_analyzer import __version__
from powerbi_analyzer.cache import RunCache
from powerbi_analyzer.collectors._sql import SqlExecutor
from powerbi_analyzer.collectors.databricks import DatabricksCollector, WorkspaceClient
from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Severity, Status
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.engine import Engine
from powerbi_analyzer.reporters.markdown import MarkdownReporter
from powerbi_analyzer.rules import RuleRegistry


def _make_databricks_clients(profile: str) -> tuple[SqlExecutor, WorkspaceClient]:
    from powerbi_analyzer.databricks_clients import (
        SdkSqlExecutor,
        SdkWorkspaceClient,
    )

    return SdkSqlExecutor(profile=profile), SdkWorkspaceClient(profile=profile)


def _exit_code(findings: Sequence[Finding], fail_on: str) -> int:
    if fail_on == "none":
        return 0
    threshold = {"warn": (Severity.ERROR, Severity.WARN), "error": (Severity.ERROR,)}[fail_on]
    has = any(f.status is Status.FAIL and f.severity in threshold for f in findings)
    return 2 if has else 0


def run_pbix(**_: object) -> int:
    raise NotImplementedError("pba pbix wiring lands in a later task")


def run_workspace(**_: object) -> int:
    raise NotImplementedError("pba workspace wiring lands in a later task")


def run_databricks(
    *,
    profile: str,
    warehouse_id: str,
    catalogs: list[str],
    lookback_days: int,
    out: Path | None,
    formats: str,
    ignore: set[str],
    fail_on: str,
) -> int:
    sql, ws = _make_databricks_clients(profile)
    collector = DatabricksCollector(
        warehouse_id=warehouse_id,
        catalogs=catalogs,
        lookback_days=lookback_days,
        sql=sql,
        ws=ws,
    )
    wh, cat = collector.collect()
    cache = RunCache()
    cache.write("warehouse", wh.model_dump(mode="json"))
    cache.write("catalog", cat.model_dump(mode="json"))

    registry = RuleRegistry.discover()
    engine = Engine(registry)
    result = engine.run(
        active_modes={"databricks"},
        context={WarehouseState: wh, CatalogState: cat},
        ignore=ignore,
    )

    md = MarkdownReporter().render(
        result,
        target_description=f"warehouse {warehouse_id}",
        modes_run=["databricks"],
        generated_at=datetime.now(UTC),
        version=__version__,
    )
    target = out or Path(f"pba-audit-{datetime.now(UTC):%Y-%m-%d}-{cache.short_id}.md")
    target.write_text(md)
    print(f"wrote {target}")
    return _exit_code(result.findings, fail_on)


def run_scan(_config: Path) -> int:
    raise NotImplementedError("pba scan wiring lands in a later task")
