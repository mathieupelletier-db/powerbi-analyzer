from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "DP-002"
NAME = "Use star schema"
PHASE = Phase.DATA_PREP
SEVERITY = Severity.INFO
APPLIES_TO = ["databricks"]
DOCS_URL = "https://learn.microsoft.com/power-bi/guidance/star-schema"


@rule(RULE_ID)
def check(catalog: CatalogState, warehouse: WarehouseState) -> Finding:
    by_name = {t.full_name: t for t in catalog.tables}
    snowflakes: list[str] = []
    for t in catalog.tables:
        if not t.full_name.split(".")[-1].lower().startswith("dim"):
            continue
        for fk in t.foreign_keys:
            ref = by_name.get(fk.to_table)
            if ref is not None and ref.full_name.split(".")[-1].lower().startswith("dim"):
                snowflakes.append(f"{t.full_name} -> {ref.full_name}")
    if not snowflakes:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="No dim-to-dim relationships detected.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(snowflakes)} dim-to-dim relationship(s) — possible snowflake.",
        evidence={
            "relationships": snowflakes,
            "heuristic": "best-effort — review and ignore if intentional",
        },
        why="Snowflake relationships add joins. Star schema is faster for typical Power BI queries.",
        fix="Denormalize dimension hierarchies into a single dim table where reasonable.",
        docs_url=DOCS_URL,
    )
