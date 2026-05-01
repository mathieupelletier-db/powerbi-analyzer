from collections import Counter

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "DP-006"
NAME = "Use auto-generated (computed) columns"
PHASE = Phase.DATA_PREP
SEVERITY = Severity.INFO
APPLIES_TO = ["databricks"]
DOCS_URL = (
    "https://docs.databricks.com/sql/language-manual/sql-ref-syntax-ddl-create-table-using.html"
)


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
    by_pattern = Counter(tuple(sorted(q.referenced_tables or [])) for q in pbi)
    repeated = sum(1 for v in by_pattern.values() if v >= 5)
    if not repeated:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="No repeated query patterns.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{repeated} query pattern(s) repeated ≥5 times — computed-column candidates.",
        evidence={
            "repeated_pattern_count": repeated,
            "heuristic": "best-effort — review and ignore if intentional",
        },
        why="Repeated DAX expressions over the same tables can be precomputed in Delta as computed columns.",
        fix="Move repeated derivations into a Delta computed column or a SQL view at the Gold layer.",
        docs_url=DOCS_URL,
    )
