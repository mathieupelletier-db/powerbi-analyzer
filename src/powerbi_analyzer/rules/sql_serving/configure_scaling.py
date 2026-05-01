from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "SS-005"
NAME = "Configure SQL warehouse scaling"
PHASE = Phase.SQL_SERVING
SEVERITY = Severity.WARN
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/admin/sql-endpoints.html#scaling"


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    queued = sum(1 for q in warehouse.query_history if q.queue_duration_ms > 1000)
    if warehouse.max_clusters > 1:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary=f"max_clusters={warehouse.max_clusters}.",
            docs_url=DOCS_URL,
        )
    if queued == 0:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="max_clusters=1 but no queueing observed.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"max_clusters=1 and {queued} query(ies) queued > 1s.",
        evidence={"max_clusters": warehouse.max_clusters, "queued_query_count": queued},
        why="With max_clusters=1 the warehouse cannot scale out, so concurrent queries queue.",
        fix="Set max_clusters >= 2 (typical: 4) so the warehouse can absorb concurrent BI traffic.",
        docs_url=DOCS_URL,
    )
