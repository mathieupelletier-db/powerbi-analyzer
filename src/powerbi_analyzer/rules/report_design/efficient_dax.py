import re

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules import rule

RULE_ID = "RD-009"
NAME = "Use efficient DAX patterns"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.WARN
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/dax/best-practices/dax-aggregators"

NESTED_FILTER = re.compile(r"FILTER\s*\(\s*FILTER", re.IGNORECASE)
SUMX_TABLE_COL = re.compile(r"SUMX\s*\(\s*([A-Za-z_][\w]*)\s*,\s*\1\[", re.IGNORECASE)


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    smelly: list[str] = []
    for m in model.measures:
        expr = m.expression
        if NESTED_FILTER.search(expr):
            smelly.append(f"{m.table}[{m.name}]: nested FILTER")
        if SUMX_TABLE_COL.search(expr):
            smelly.append(f"{m.table}[{m.name}]: SUMX(table, table[col]) — prefer SUM")
    if not smelly:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="No DAX smells matched.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(smelly)} DAX measure(s) match efficiency anti-patterns.",
        evidence={"matches": smelly, "heuristic": "best-effort — review and ignore if intentional"},
        why="Nested FILTER and SUMX(t, t[c]) are common slow patterns. SUM(t[c]) is much faster.",
        fix="Replace SUMX(t, t[c]) with SUM(t[c]); collapse nested FILTERs into a single predicate.",
        docs_url=DOCS_URL,
    )
