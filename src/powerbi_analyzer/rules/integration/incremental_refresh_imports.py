from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel, StorageMode
from powerbi_analyzer.rules import rule

RULE_ID = "IN-005"
NAME = "Use incremental refresh for large Import tables"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.WARN
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/connect-data/incremental-refresh-overview"

ROW_LIMIT = 1_000_000


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    bad: list[str] = []
    for t in model.tables:
        if t.storage_mode is not StorageMode.IMPORT:
            continue
        if (t.row_count or 0) <= ROW_LIMIT:
            continue
        if not any(p.refresh_policy for p in t.partitions):
            bad.append(t.name)
    if not bad:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="All large Import tables use incremental refresh.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(bad)} large Import table(s) without RefreshPolicy.",
        evidence={"tables": bad, "row_threshold": ROW_LIMIT},
        why="Without incremental refresh, every refresh re-imports the full table — slow and brittle.",
        fix="Define a RefreshPolicy with rolling window + incremental window in Power BI.",
        docs_url=DOCS_URL,
    )
