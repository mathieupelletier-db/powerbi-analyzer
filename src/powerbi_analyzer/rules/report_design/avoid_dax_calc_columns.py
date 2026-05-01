from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules import rule

RULE_ID = "RD-011"
NAME = "Avoid DAX calculated columns and calculated tables"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.WARN
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/guidance/import-modeling-data-reduction"


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    cols = [f"{c.table}[{c.name}]" for c in model.calculated_columns]
    tabs = [t.name for t in model.calculated_tables]
    if not cols and not tabs:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="No DAX calculated columns or tables.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(cols)} calculated column(s); {len(tabs)} calculated table(s).",
        evidence={"calculated_columns": cols, "calculated_tables": tabs},
        why="Calculated columns / tables increase semantic-model size and refresh time. Doing the same work in Gold Delta is faster and shareable.",
        fix="Move calculated columns into the Gold view (or a derived column at ETL time). Replace calculated tables with persisted tables.",
        docs_url=DOCS_URL,
    )
