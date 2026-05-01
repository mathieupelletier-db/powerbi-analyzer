from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules import rule

RULE_ID = "RD-001"
NAME = "Limit visuals per page"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.WARN
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/guidance/power-bi-optimization"

LIMIT = 12


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    over = {p: len(v) for p, v in model.visuals_by_page.items() if len(v) > LIMIT}
    if not over:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary=f"Each page has ≤ {LIMIT} visuals.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(over)} page(s) exceed {LIMIT} visuals.",
        evidence={"pages": over, "threshold": LIMIT},
        why="Each visual fires its own DAX query; many on one page multiplies load and memory.",
        fix="Split into multiple pages, hide rarely-used visuals, or use bookmarks/personalization.",
        docs_url=DOCS_URL,
    )
