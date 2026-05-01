from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel, StorageMode
from powerbi_analyzer.rules import rule

RULE_ID = "IN-002"
NAME = "Use DirectQuery on facts and Dual on dimensions"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.WARN
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/transform-model/desktop-storage-mode"

LARGE_FACT = 1_000_000


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    fact_violations: list[str] = []
    dim_violations: list[str] = []
    for t in model.tables:
        n = t.name.lower()
        is_fact = n.startswith("fact") or "fact_" in n or (t.row_count or 0) > LARGE_FACT
        is_dim = n.startswith("dim") or "dim_" in n
        if is_fact and t.storage_mode is StorageMode.IMPORT:
            fact_violations.append(t.name)
        if is_dim and t.storage_mode is StorageMode.IMPORT and (t.row_count or 0) < 100_000:
            dim_violations.append(t.name)
    if not fact_violations and not dim_violations:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="Storage modes look appropriate.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(fact_violations)} fact(s) in Import, {len(dim_violations)} dim(s) not in Dual.",
        evidence={
            "facts_in_import": fact_violations,
            "dims_not_dual": dim_violations,
            "heuristic": "best-effort — review and ignore if intentional",
        },
        why="Import-mode facts can outgrow capacity; Dual dims allow dim filters to fold into either path.",
        fix="Set fact tables to DirectQuery, small dimensions to Dual.",
        docs_url=DOCS_URL,
    )
