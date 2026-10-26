from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule
from powerbi_analyzer.rules._attribution import attribution_gap

RULE_ID = "DP-004"
NAME = "Declare PK/FK with RELY"
PHASE = Phase.DATA_PREP
SEVERITY = Severity.ERROR
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/tables/constraints.html"


@rule(RULE_ID)
def check(catalog: CatalogState, warehouse: WarehouseState) -> Finding:
    gap = attribution_gap(catalog, warehouse)
    if gap:
        return Finding.not_applicable(
            RULE_ID, NAME, phase=PHASE, target=warehouse.name, reason=gap, docs_url=DOCS_URL
        )
    referenced = set(catalog.referenced_by_powerbi)
    no_pk: list[str] = []
    no_rely: list[str] = []
    rely_unknown: list[str] = []
    for t in catalog.tables:
        if t.full_name not in referenced:
            continue
        if not t.primary_key:
            no_pk.append(t.full_name)
        elif t.rely is None:
            rely_unknown.append(t.full_name)
        elif not t.rely:
            no_rely.append(t.full_name)
    if not no_pk and not no_rely and rely_unknown:
        return Finding.not_applicable(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            reason=(
                f"PKs exist but RELY could not be verified for {len(rely_unknown)} table(s) "
                "(UC Tables API unavailable); check with SHOW CREATE TABLE"
            ),
            docs_url=DOCS_URL,
        )
    if not no_pk and not no_rely:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="All Power BI tables have PK constraints with RELY.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(no_pk)} table(s) missing PK; {len(no_rely)} have PK without RELY.",
        evidence={"missing_pk": no_pk, "pk_without_rely": no_rely, "rely_unverified": rely_unknown},
        why="Without RELY-enforced PKs, Power BI cannot use Assume Referential Integrity and Databricks loses optimizer hints.",
        fix="ALTER TABLE ... ADD CONSTRAINT pk_<name> PRIMARY KEY (...) RELY; for each Gold table.",
        docs_url=DOCS_URL,
    )
