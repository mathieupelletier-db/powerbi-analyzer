from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules import rule

RULE_ID = "RD-006"
NAME = "Use Assume Referential Integrity where valid"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.WARN
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/transform-model/desktop-relationships-troubleshoot"


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    candidates: list[str] = []
    cols_by_table = {t.name: {c.name: c for c in t.columns} for t in model.tables}
    for r in model.relationships:
        if r.cardinality not in {"one-to-many", "many-to-one"}:
            continue
        if r.assume_referential_integrity:
            continue
        from_col = cols_by_table.get(r.from_table, {}).get(r.from_column)
        if from_col is not None and not from_col.is_nullable:
            candidates.append(f"{r.from_table}[{r.from_column}] → {r.to_table}[{r.to_column}]")
    if not candidates:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="No NOT NULL fact-to-dim relationships missing ARI.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(candidates)} relationship(s) eligible for Assume Referential Integrity.",
        evidence={"relationships": candidates},
        why="ARI lets Power BI emit INNER JOIN instead of LEFT OUTER, simplifying generated SQL.",
        fix="If the foreign key is enforced upstream, enable Assume Referential Integrity on the relationship.",
        docs_url=DOCS_URL,
    )
