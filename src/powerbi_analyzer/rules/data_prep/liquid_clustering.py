from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "DP-007"
NAME = "Use Liquid Clustering or Z-order"
PHASE = Phase.DATA_PREP
SEVERITY = Severity.WARN
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/delta/clustering.html"

LARGE_TABLE_BYTES = 10 * 1024**3


@rule(RULE_ID)
def check(catalog: CatalogState, warehouse: WarehouseState) -> Finding:
    referenced = set(catalog.referenced_by_powerbi)
    bad: list[str] = []
    for t in catalog.tables:
        if t.full_name not in referenced:
            continue
        if (t.size_bytes or 0) > LARGE_TABLE_BYTES and t.clustering.kind == "none":
            bad.append(t.full_name)
    if not bad:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="All large PBI tables have clustering configured.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(bad)} large table(s) without Liquid Clustering or Z-order.",
        evidence={"tables": bad, "threshold_bytes": LARGE_TABLE_BYTES},
        why="Without clustering, large Delta tables incur full scans on column-targeted queries.",
        fix="Add Liquid Clustering on the most-filtered columns: ALTER TABLE ... CLUSTER BY (...).",
        docs_url=DOCS_URL,
    )
