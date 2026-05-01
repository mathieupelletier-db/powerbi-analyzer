from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules import rule

RULE_ID = "IN-008"
NAME = "Use parameters for environment switching"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.INFO
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/connect-data/desktop-dynamic-m-query-parameters"


_KEYWORDS = {"server", "host", "warehouse", "endpoint", "url"}


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    has_param_for_endpoint = any(
        any(kw in p.name.lower() for kw in _KEYWORDS) for p in model.parameters
    )
    if has_param_for_endpoint:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="Connection endpoint parameter detected.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary="No parameter found for switching connection endpoints.",
        evidence={
            "parameters": [p.name for p in model.parameters],
            "heuristic": "best-effort — review and ignore if intentional",
        },
        why="Hardcoded warehouse URLs make dev → prod migration painful.",
        fix="Define an M parameter (e.g., 'warehouse_endpoint') and reference it in the connection string.",
        docs_url=DOCS_URL,
    )
