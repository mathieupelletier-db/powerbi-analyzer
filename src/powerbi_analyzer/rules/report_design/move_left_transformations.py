import re

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules import rule

RULE_ID = "RD-008"
NAME = "Move transformations left (prefer SQL views)"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.WARN
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/guidance/power-query-folding"

PATTERNS = [r"Table\.AddColumn", r"Table\.Group", r"Table\.NestedJoin", r"Table\.Pivot"]
M_PATTERN = re.compile("|".join(PATTERNS))


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    offenders: list[str] = []
    for t in model.tables:
        for p in t.partitions:
            if p.source_type != "m" or not p.source_expression:
                continue
            hits = M_PATTERN.findall(p.source_expression)
            if hits:
                offenders.append(f"{t.name}: {sorted(set(hits))}")
    if not offenders:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="No M transformations matching the move-left heuristic.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(offenders)} table(s) perform M transformations that could be SQL views.",
        evidence={
            "tables": offenders,
            "heuristic": "best-effort — review and ignore if intentional",
        },
        why="Power Query transformations are slower and harder to share than SQL views in Databricks.",
        fix="Move AddColumn/Group/Join/Pivot to a Gold-layer SQL view; have Power BI just SELECT from it.",
        docs_url=DOCS_URL,
    )
