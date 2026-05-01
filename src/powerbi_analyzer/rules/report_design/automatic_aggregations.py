from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel, StorageMode
from powerbi_analyzer.rules import rule

RULE_ID = "RD-004"
NAME = "Enable automatic aggregations for DirectQuery"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.INFO
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/transform-model/aggregations-auto"


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    has_dq = any(t.storage_mode is StorageMode.DIRECT_QUERY for t in model.tables)
    has_auto = bool(model.aggregations) or any(t.is_aggregation_table for t in model.tables)
    if not has_dq:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="No DirectQuery tables; rule N/A.",
            docs_url=DOCS_URL,
        )
    if has_auto:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="Aggregations already mapped.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary="DirectQuery model without automatic aggregations enabled.",
        evidence={
            "directquery_tables": [
                t.name for t in model.tables if t.storage_mode is StorageMode.DIRECT_QUERY
            ]
        },
        why="Automatic aggregations cache hot DirectQuery query results, often eliminating the slow path.",
        fix="In Power BI Service, enable Automatic Aggregations on this dataset.",
        docs_url=DOCS_URL,
    )
