from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "SS-009"
NAME = "Reasonable starting warehouse size"
PHASE = Phase.SQL_SERVING
SEVERITY = Severity.INFO
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/admin/sql-endpoints.html#sizes"


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    if warehouse.cluster_size != "2X-Small":
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary=f"Size {warehouse.cluster_size}.",
            docs_url=DOCS_URL,
        )
    queued = any(q.queue_duration_ms > 1000 for q in warehouse.query_history)
    spilled = any(q.spilled_to_disk for q in warehouse.query_history)
    if not queued and not spilled:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="2X-Small with no queueing or spills.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary="2X-Small warehouse with queueing/spills.",
        evidence={"queued": queued, "spilled": spilled},
        why="2X-Small is appropriate for very low-traffic dev only. Production BI will queue or spill.",
        fix="Start at Medium for production BI workloads; tune from there based on monitoring.",
        docs_url=DOCS_URL,
    )
