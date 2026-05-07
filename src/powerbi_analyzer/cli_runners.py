"""CLI command implementations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import typer

from powerbi_analyzer import __version__
from powerbi_analyzer.cache import RunCache
from powerbi_analyzer.collectors._sql import SqlExecutor
from powerbi_analyzer.collectors.databricks import DatabricksCollector, WorkspaceClient
from powerbi_analyzer.collectors.pbix import PbixCollector
from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Severity, Status
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.engine import Engine, RunResult
from powerbi_analyzer.reporters.markdown import MarkdownReporter
from powerbi_analyzer.rules import RuleRegistry


def _make_databricks_clients(
    profile: str, warehouse_id: str | None = None
) -> tuple[SqlExecutor, WorkspaceClient]:
    from powerbi_analyzer.databricks_clients import (
        SdkSqlExecutor,
        SdkWorkspaceClient,
    )

    return (
        SdkSqlExecutor(profile=profile, warehouse_id=warehouse_id),
        SdkWorkspaceClient(profile=profile),
    )


def _exit_code(findings: Sequence[Finding], fail_on: str) -> int:
    if fail_on == "none":
        return 0
    threshold = {"warn": (Severity.ERROR, Severity.WARN), "error": (Severity.ERROR,)}[fail_on]
    has = any(f.status is Status.FAIL and f.severity in threshold for f in findings)
    return 2 if has else 0


def _ext_for_formats(formats: str) -> str:
    """File suffix to use when --out is not provided. HTML wins if requested."""
    return ".html" if "html" in formats.lower() else ".md"


def _resolve_target(out: Path | None, formats: str, short_id: str) -> Path:
    """Pick output path, defaulting to a timestamped file with the right suffix.

    If --out is provided, honor it as-is so the user can override the suffix.
    Otherwise pick .html when --formats includes html, else .md.
    """
    if out is not None:
        return out
    ext = _ext_for_formats(formats)
    return Path(f"pba-audit-{datetime.now(UTC):%Y-%m-%d}-{short_id}{ext}")


def _write_report(
    result: RunResult,
    *,
    target: Path,
    formats: str,
    target_description: str,
    modes_run: list[str],
) -> None:
    """Render and write a report, choosing renderer by file extension or formats flag."""
    from powerbi_analyzer.reporters.html import HtmlReporter

    use_html = target.suffix.lower() == ".html" or "html" in formats.lower()
    now = datetime.now(UTC)
    if use_html:
        content = HtmlReporter().render(
            result,
            target_description=target_description,
            modes_run=modes_run,
            generated_at=now,
            version=__version__,
        )
    else:
        content = MarkdownReporter().render(
            result,
            target_description=target_description,
            modes_run=modes_run,
            generated_at=now,
            version=__version__,
        )
    target.write_text(content)
    print(f"wrote {target}")


def run_pbix(
    *,
    paths: list[Path],
    out: Path | None,
    out_dir: Path | None,
    formats: str,
    severity_threshold: str,
    ignore: set[str],
    fail_on: str,
) -> int:
    cache = RunCache()
    all_findings: list[Finding] = []
    result = None
    for p in paths:
        model = PbixCollector(path=p).collect()
        cache.write(f"pbix-{p.stem}", model.model_dump(mode="json"))
        registry = RuleRegistry.discover()
        engine = Engine(registry)
        result = engine.run(
            active_modes={"pbix"},
            context={SemanticModel: model},
            ignore=ignore,
        )
        all_findings.extend(result.findings)

    if result is None:
        # No paths provided — nothing to report
        return 0

    target = _resolve_target(out, formats, cache.short_id)
    _write_report(
        result,
        target=target,
        formats=formats,
        target_description=", ".join(p.name for p in paths),
        modes_run=["pbix"],
    )
    return _exit_code(all_findings, fail_on)


def run_workspace(
    *,
    workspace_id: str,
    tenant_id: str | None,
    dataset_ids: list[str],
    auth: str,
    out: Path | None,
    formats: str,
    ignore: set[str],
    fail_on: str,
) -> int:
    from powerbi_analyzer.auth_msal import get_token
    from powerbi_analyzer.collectors.workspace import (
        HttpPowerBiRestClient,
        HttpXmlaRestClient,
        WorkspaceCollector,
    )
    from powerbi_analyzer.domain.semantic_model import WorkspaceConfig

    if not tenant_id:
        raise typer.BadParameter("--tenant-id is required for workspace mode")
    token = get_token(tenant_id=tenant_id, auth=auth)
    rest = HttpPowerBiRestClient(token)
    xmla = HttpXmlaRestClient(token)
    sm, cfg = WorkspaceCollector(
        workspace_id=workspace_id,
        dataset_ids=dataset_ids or None,
        rest=rest,
        xmla=xmla,
    ).collect()
    cache = RunCache()
    cache.write("workspace_model", sm.model_dump(mode="json"))
    cache.write("workspace_config", cfg.model_dump(mode="json"))
    registry = RuleRegistry.discover()
    engine = Engine(registry)
    result = engine.run(
        active_modes={"workspace"},
        context={SemanticModel: sm, WorkspaceConfig: cfg},
        ignore=ignore,
    )
    target = _resolve_target(out, formats, cache.short_id)
    _write_report(
        result,
        target=target,
        formats=formats,
        target_description=f"workspace {workspace_id}",
        modes_run=["workspace"],
    )
    return _exit_code(result.findings, fail_on)


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
    sql, ws = _make_databricks_clients(profile, warehouse_id=warehouse_id)
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

    target = _resolve_target(out, formats, cache.short_id)
    _write_report(
        result,
        target=target,
        formats=formats,
        target_description=f"warehouse {warehouse_id}",
        modes_run=["databricks"],
    )
    return _exit_code(result.findings, fail_on)


def run_scan(config_path: Path) -> int:
    from glob import glob

    from powerbi_analyzer.collectors.pbix import PbixCollector
    from powerbi_analyzer.config import load_config
    from powerbi_analyzer.domain.catalog import CatalogState
    from powerbi_analyzer.domain.semantic_model import SemanticModel, WorkspaceConfig
    from powerbi_analyzer.domain.warehouse import WarehouseState
    from powerbi_analyzer.reporters.html import HtmlReporter

    cfg = load_config(config_path)
    cache = RunCache()
    context: dict[type, object] = {}
    active: set[str] = set()
    target_desc_parts: list[str] = []

    if cfg.pbix.files:
        # v1: only the first matched file (extending to many is later)
        for pattern in cfg.pbix.files:
            for path in glob(pattern):
                model = PbixCollector(path=Path(path)).collect()
                context[SemanticModel] = model
                active.add("pbix")
                target_desc_parts.append(Path(path).name)
                break
            else:
                continue
            break

    if cfg.databricks.warehouse_id:
        sql, ws = _make_databricks_clients(
            cfg.databricks.profile, warehouse_id=cfg.databricks.warehouse_id
        )
        wh, cat = DatabricksCollector(
            warehouse_id=cfg.databricks.warehouse_id,
            catalogs=cfg.databricks.catalogs,
            lookback_days=cfg.databricks.query_history_lookback_days,
            sql=sql,
            ws=ws,
        ).collect()
        context[WarehouseState] = wh
        context[CatalogState] = cat
        active.add("databricks")
        target_desc_parts.append(f"warehouse {wh.warehouse_id}")

    if cfg.workspace.workspace_id:
        from powerbi_analyzer.auth_msal import get_token
        from powerbi_analyzer.collectors.workspace import (
            HttpPowerBiRestClient,
            HttpXmlaRestClient,
            WorkspaceCollector,
        )

        token = get_token(tenant_id=cfg.workspace.tenant_id, auth=cfg.workspace.auth)
        ds_ids = None if cfg.workspace.datasets == "auto" else cfg.workspace.datasets
        sm, wcfg = WorkspaceCollector(
            workspace_id=cfg.workspace.workspace_id,
            dataset_ids=ds_ids if isinstance(ds_ids, list) else None,
            rest=HttpPowerBiRestClient(token),
            xmla=HttpXmlaRestClient(token),
        ).collect()
        context[SemanticModel] = sm
        context[WorkspaceConfig] = wcfg
        active.add("workspace")
        target_desc_parts.append(f"workspace {wcfg.workspace_id}")

    registry = RuleRegistry.discover()
    engine = Engine(registry)
    result = engine.run(active_modes=active, context=context, ignore=set(cfg.rules.ignore))
    target_desc = ", ".join(target_desc_parts) or "(no targets)"

    out_dir = Path(cfg.output.dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"pba-audit-{datetime.now(UTC):%Y-%m-%d}-{cache.short_id}"
    if "markdown" in cfg.output.formats:
        md = MarkdownReporter().render(
            result,
            target_description=target_desc,
            modes_run=sorted(active),
            generated_at=datetime.now(UTC),
            version=__version__,
        )
        (out_dir / f"{base}.md").write_text(md)
    if "html" in cfg.output.formats:
        html = HtmlReporter().render(
            result,
            target_description=target_desc,
            modes_run=sorted(active),
            generated_at=datetime.now(UTC),
            version=__version__,
        )
        (out_dir / f"{base}.html").write_text(html)
    print(f"wrote {base}.{'+'.join(cfg.output.formats)} to {out_dir}")
    return 0
