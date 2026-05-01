from datetime import UTC, datetime, timedelta

from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "DP-008"
NAME = "Predictive Optimization or recent OPTIMIZE/VACUUM"
PHASE = Phase.DATA_PREP
SEVERITY = Severity.WARN
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/optimizations/predictive-optimization.html"

STALE_DAYS = 30


@rule(RULE_ID)
def check(catalog: CatalogState, warehouse: WarehouseState) -> Finding:
    cutoff = datetime.now(UTC) - timedelta(days=STALE_DAYS)
    referenced = set(catalog.referenced_by_powerbi)
    bad: list[str] = []
    for t in catalog.tables:
        if t.full_name not in referenced or t.predictive_optimization:
            continue
        opt_stale = t.last_optimize_at is None or t.last_optimize_at < cutoff
        vac_stale = t.last_vacuum_at is None or t.last_vacuum_at < cutoff
        if opt_stale or vac_stale:
            bad.append(t.full_name)
    if not bad:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="All PBI tables either use Predictive Optimization or were recently optimized.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(bad)} PBI table(s) without PO and stale OPTIMIZE/VACUUM (> {STALE_DAYS}d).",
        evidence={"tables": bad, "stale_days_threshold": STALE_DAYS},
        why="Without Predictive Optimization or routine OPTIMIZE/VACUUM, tables accumulate small files and stale stats.",
        fix="Enable Predictive Optimization at the catalog level, or schedule weekly OPTIMIZE + VACUUM.",
        docs_url=DOCS_URL,
    )
