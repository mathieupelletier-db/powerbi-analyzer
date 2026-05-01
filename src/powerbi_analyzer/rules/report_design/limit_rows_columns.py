from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel, StorageMode
from powerbi_analyzer.rules import rule

RULE_ID = "RD-002"
NAME = "Limit rows and columns surfaced in DirectQuery"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.WARN
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/guidance/power-bi-optimization"

WIDE_LIMIT = 50


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    wide = {
        t.name: len(t.columns)
        for t in model.tables
        if t.storage_mode is StorageMode.DIRECT_QUERY and len(t.columns) > WIDE_LIMIT
    }
    if not wide:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary=f"No DirectQuery table has > {WIDE_LIMIT} columns.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(wide)} DirectQuery table(s) wider than {WIDE_LIMIT} columns.",
        evidence={"tables": wide, "threshold": WIDE_LIMIT},
        why="Wide DirectQuery tables generate large generated SQL and slow visuals.",
        fix="Project only the columns Power BI needs; use views to narrow.",
        docs_url=DOCS_URL,
    )
