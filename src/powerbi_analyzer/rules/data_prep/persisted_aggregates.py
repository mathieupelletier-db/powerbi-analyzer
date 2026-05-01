from collections import Counter

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "DP-003"
NAME = "Use SQL views or persisted tables for repeated aggregations"
PHASE = Phase.DATA_PREP
SEVERITY = Severity.INFO
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/user/queries/index.html"


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    pbi = [
        q
        for q in warehouse.query_history
        if (q.client_application or "").lower().startswith("power bi")
    ]
    if not pbi:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="No Power BI history.",
            docs_url=DOCS_URL,
        )
    by_target = Counter(tuple(sorted(q.referenced_tables or [])) for q in pbi)
    repeated = {",".join(k): v for k, v in by_target.items() if k and v >= 5}
    if not repeated:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="No frequently-repeated table sets.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(repeated)} table-set(s) hit ≥ 5 times — pre-aggregation candidate.",
        evidence={
            "repeated_table_sets": repeated,
            "heuristic": "best-effort — review and ignore if intentional",
        },
        why="Repeatedly aggregating the same fact set wastes compute. A persisted aggregate table or view can serve the same answer instantly.",
        fix="Build a Gold-layer aggregate table (or SQL view) at the granularity Power BI requests; map it via aggregations.",
        docs_url=DOCS_URL,
    )
