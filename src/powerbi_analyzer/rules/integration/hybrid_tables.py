from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel, StorageMode
from powerbi_analyzer.rules import rule

RULE_ID = "IN-004"
NAME = "Consider hybrid tables for large facts"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.INFO
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = (
    "https://learn.microsoft.com/power-bi/connect-data/desktop-incremental-refresh#hybrid-tables"
)

LARGE = 50_000_000


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    candidates = [
        t.name
        for t in model.tables
        if t.storage_mode is StorageMode.DIRECT_QUERY
        and (t.row_count or 0) > LARGE
        and not t.is_aggregation_table
        and not any(p.refresh_policy and p.refresh_policy.real_time for p in t.partitions)
    ]
    if not candidates:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="No large pure-DirectQuery facts found.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(candidates)} large fact(s) candidate for hybrid tables.",
        evidence={
            "tables": candidates,
            "row_threshold": LARGE,
            "heuristic": "best-effort — review and ignore if intentional",
        },
        why="Hybrid tables import historical data and DirectQuery the hot tail — best of both for huge facts.",
        fix="Configure incremental refresh with real-time partition (hybrid table).",
        docs_url=DOCS_URL,
    )
