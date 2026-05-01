from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "SS-001"
NAME = "Use SQL warehouse, not all-purpose cluster"
PHASE = Phase.SQL_SERVING
SEVERITY = Severity.ERROR
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/admin/sql-endpoints.html"


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    offenders = [
        q
        for q in warehouse.query_history
        if (q.client_application or "").lower().startswith("power bi") and q.all_purpose_cluster_id
    ]
    target = warehouse.name
    if not offenders:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=target,
            summary="No Power BI queries observed on all-purpose clusters.",
            docs_url=DOCS_URL,
        )
    clusters = sorted({f"{q.all_purpose_cluster_id} ({q.client_application})" for q in offenders})
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=target,
        severity=SEVERITY,
        summary=f"{len(offenders)} Power BI query(ies) ran on all-purpose cluster(s).",
        evidence={"clusters": clusters, "query_count": len(offenders)},
        why="All-purpose clusters cost more and lack BI workload optimizations available on SQL warehouses.",
        fix="Point Power BI at a SQL warehouse instead. Migrate any custom JDBC URLs to the warehouse endpoint.",
        docs_url=DOCS_URL,
    )
