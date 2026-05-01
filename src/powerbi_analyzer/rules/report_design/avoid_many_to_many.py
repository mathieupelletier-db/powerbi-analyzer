from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules import rule

RULE_ID = "RD-005"
NAME = "Avoid many-to-many relationships"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.WARN
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/transform-model/desktop-many-to-many-relationships"


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    m2m = [r for r in model.relationships if r.cardinality == "many-to-many"]
    target = model.name
    if not m2m:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=target,
            summary="No many-to-many relationships found.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=target,
        severity=SEVERITY,
        summary=f"{len(m2m)} many-to-many relationship(s) detected.",
        evidence={"relationships": [f"{r.from_table}↔{r.to_table}" for r in m2m]},
        why="Many-to-many relationships add bridge-table complexity and can degrade query plans.",
        fix="Replace with a bridge dimension or denormalize at the gold layer.",
        docs_url=DOCS_URL,
    )
