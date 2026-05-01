from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "DP-005"
NAME = "Avoid wide and high-cardinality types"
PHASE = Phase.DATA_PREP
SEVERITY = Severity.WARN
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/tables/index.html"

STRING_LIMIT = 1000


@rule(RULE_ID)
def check(catalog: CatalogState, warehouse: WarehouseState) -> Finding:
    referenced = set(catalog.referenced_by_powerbi)
    offenders: list[str] = []
    for t in catalog.tables:
        if t.full_name not in referenced:
            continue
        for c in t.columns:
            dt = c.data_type.lower()
            if dt.startswith(("binary", "struct", "array", "map")):
                offenders.append(f"{t.full_name}.{c.name} ({c.data_type})")
            elif dt.startswith("string") and (c.max_length_observed or 0) > STRING_LIMIT:
                offenders.append(
                    f"{t.full_name}.{c.name} (string, observed {c.max_length_observed})"
                )
    if not offenders:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="No wide or high-cardinality column types in Power BI tables.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(offenders)} wide/complex column(s) flagged.",
        evidence={"columns": offenders, "string_max_length_threshold": STRING_LIMIT},
        why="Wide strings, BINARY, and complex types inflate Power BI semantic-model size and slow queries.",
        fix="Project narrower types in your Gold view, drop unused complex columns, or move large blobs to a separate table.",
        docs_url=DOCS_URL,
    )
