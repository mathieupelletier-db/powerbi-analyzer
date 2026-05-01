from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "SS-006"
NAME = "Increase min clusters for concurrent traffic"
PHASE = Phase.SQL_SERVING
SEVERITY = Severity.WARN
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/admin/sql-endpoints.html#scaling"


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    long_waits = sum(1 for q in warehouse.query_history if q.queue_duration_ms > 5000)
    if warehouse.min_clusters > 1 or long_waits == 0:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary=f"min_clusters={warehouse.min_clusters}; long waits={long_waits}.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{long_waits} query(ies) waited >5s with min_clusters=1.",
        evidence={"min_clusters": warehouse.min_clusters, "long_wait_count": long_waits},
        why="When min_clusters=1, the warehouse must scale out from cold each time concurrency rises.",
        fix="Raise min_clusters to 2 to keep capacity warm during business hours.",
        docs_url=DOCS_URL,
    )
