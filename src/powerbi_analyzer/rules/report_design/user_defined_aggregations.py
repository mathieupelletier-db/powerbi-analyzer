from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel, StorageMode
from powerbi_analyzer.rules import rule

RULE_ID = "RD-003"
NAME = "Use user-defined aggregations on large fact tables"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.INFO
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/transform-model/aggregations-advanced"

LARGE_ROWS = 100_000_000


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    big_dq = [
        t
        for t in model.tables
        if t.storage_mode is StorageMode.DIRECT_QUERY
        and (t.row_count or 0) > LARGE_ROWS
        and not t.is_aggregation_table
    ]
    has_agg = any(t.is_aggregation_table for t in model.tables) or model.aggregations
    if not big_dq or has_agg:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="No large unsupported fact, or aggregations already mapped.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(big_dq)} large DirectQuery fact(s) without aggregation tables.",
        evidence={"tables": [t.name for t in big_dq], "row_threshold": LARGE_ROWS},
        why="Without aggregations, every BI query hits the full fact, slowing typical roll-ups.",
        fix="Build a Gold-layer aggregation table at the most-queried grain and map it via Power BI Aggregations.",
        docs_url=DOCS_URL,
    )
