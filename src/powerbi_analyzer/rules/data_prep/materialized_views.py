from collections import Counter

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "DP-010"
NAME = "Evaluate materialized views"
PHASE = Phase.DATA_PREP
SEVERITY = Severity.INFO
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/user/materialized-views.html"


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
    candidates = {",".join(k): v for k, v in by_target.items() if k and v >= 3}
    if not candidates:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="No repeated table-set patterns.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(candidates)} repeated query pattern(s) — MV candidates.",
        evidence={
            "candidates": candidates,
            "heuristic": "best-effort — review and ignore if intentional",
        },
        why="Materialized views serve repeated aggregations from precomputed results.",
        fix="Create a materialized view for the most-repeated aggregation patterns.",
        docs_url=DOCS_URL,
    )
