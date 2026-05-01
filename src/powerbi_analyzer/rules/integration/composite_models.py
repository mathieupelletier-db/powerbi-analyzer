from collections import Counter

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules import rule

RULE_ID = "IN-003"
NAME = "Consider composite models"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.INFO
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/transform-model/desktop-composite-models"


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    if not model.tables:
        return Finding.passed(
            RULE_ID, NAME, phase=PHASE, target=model.name, summary="No tables.", docs_url=DOCS_URL
        )
    modes = Counter(t.storage_mode for t in model.tables)
    if len(modes) > 1:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="Composite model already in use.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"All {len(model.tables)} tables use the same storage mode.",
        evidence={
            "storage_mode": next(iter(modes)),
            "table_count": len(model.tables),
            "heuristic": "best-effort — review and ignore if intentional",
        },
        why="A composite model lets you mix Import (small dims) and DirectQuery (large facts) for both freshness and speed.",
        fix="Convert dimensions to Dual or facts to DirectQuery as appropriate.",
        docs_url=DOCS_URL,
    )
