from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "DP-001"
NAME = "Adopt medallion architecture (serve Gold)"
PHASE = Phase.DATA_PREP
SEVERITY = Severity.WARN
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/lakehouse/medallion.html"


@rule(RULE_ID)
def check(catalog: CatalogState, warehouse: WarehouseState) -> Finding:
    referenced = set(catalog.referenced_by_powerbi)
    by_name = {t.full_name: t for t in catalog.tables}
    non_gold = sorted(
        full for full in referenced if full in by_name and by_name[full].layer != "gold"
    )
    if not non_gold:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="All Power BI-referenced tables are in Gold-layer schemas.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(non_gold)} table(s) read by Power BI live outside Gold-layer schemas.",
        evidence={
            "tables": non_gold,
            "heuristic": "schema name not in {gold, serving, mart, marts, presentation}",
        },
        why="Serving from Bronze/Silver couples reports to raw or in-progress data and bypasses Gold-layer optimizations.",
        fix="Move Power BI to read from Gold (or a serving schema). Keep Bronze/Silver for ingestion and curation only.",
        docs_url=DOCS_URL,
    )
