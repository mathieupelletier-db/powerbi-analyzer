from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule
from powerbi_analyzer.rules._attribution import attribution_gap

RULE_ID = "DP-009"
NAME = "Compute column statistics"
PHASE = Phase.DATA_PREP
SEVERITY = Severity.INFO
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/language-manual/sql-ref-syntax-aux-analyze-table.html"


@rule(RULE_ID)
def check(catalog: CatalogState, warehouse: WarehouseState) -> Finding:
    gap = attribution_gap(catalog, warehouse)
    if gap:
        return Finding.not_applicable(
            RULE_ID, NAME, phase=PHASE, target=warehouse.name, reason=gap, docs_url=DOCS_URL
        )
    referenced = set(catalog.referenced_by_powerbi)
    known = [
        t for t in catalog.tables if t.full_name in referenced and t.has_column_stats is not None
    ]
    if not known:
        return Finding.not_applicable(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            reason="column statistics are not collected for the Power BI tables",
            docs_url=DOCS_URL,
        )
    bad = sorted(t.full_name for t in known if not t.has_column_stats)
    if not bad:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="All PBI tables have column statistics.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(bad)} PBI table(s) lack column statistics.",
        evidence={"tables": bad},
        why="Without statistics, the optimizer makes worse join-strategy and pruning decisions.",
        fix="Run ANALYZE TABLE ... COMPUTE STATISTICS FOR ALL COLUMNS, or enable Automatic Statistics.",
        docs_url=DOCS_URL,
    )
