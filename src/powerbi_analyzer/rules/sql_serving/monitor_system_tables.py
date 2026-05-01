from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "SS-010"
NAME = "Monitor via system tables"
PHASE = Phase.SQL_SERVING
SEVERITY = Severity.INFO
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/admin/system-tables/index.html"


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    scaling_events = [e for e in warehouse.events if "SCALED" in e.event_type]
    if not scaling_events:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="No scaling events in lookback window.",
            docs_url=DOCS_URL,
        )
    if warehouse.max_clusters > 1 and warehouse.min_clusters > 0:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary=f"{len(scaling_events)} scaling event(s); scaling configured.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(scaling_events)} scaling event(s) but min/max not tuned.",
        evidence={
            "scaling_event_count": len(scaling_events),
            "min_clusters": warehouse.min_clusters,
            "max_clusters": warehouse.max_clusters,
        },
        why="warehouse_events shows the warehouse is scaling, but scaling parameters look untuned.",
        fix="Inspect system.compute.warehouse_events and adjust min/max clusters to match observed concurrency.",
        docs_url=DOCS_URL,
    )
