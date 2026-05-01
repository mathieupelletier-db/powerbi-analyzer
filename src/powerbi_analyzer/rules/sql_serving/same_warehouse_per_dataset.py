from collections import defaultdict

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "SS-007"
NAME = "Same warehouse for same dataset"
PHASE = Phase.SQL_SERVING
SEVERITY = Severity.INFO
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/admin/sql-endpoints.html#cache"


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    by_table: dict[str, set[str]] = defaultdict(set)
    for q in warehouse.query_history:
        if not (q.client_application or "").lower().startswith("power bi"):
            continue
        wh_id = q.warehouse_id or q.all_purpose_cluster_id or "unknown"
        for t in q.referenced_tables or []:
            by_table[t].add(wh_id)
    fragmented = {t: sorted(wh) for t, wh in by_table.items() if len(wh) > 1}
    if not fragmented:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="No table seen across multiple warehouses.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"{len(fragmented)} table(s) hit by multiple warehouses (cache fragmentation).",
        evidence={"tables": fragmented},
        why="Each warehouse keeps its own result and disk cache. The same dataset hit from two warehouses pays double cold-start.",
        fix="Route a given Power BI dataset to one warehouse. Use separate warehouses for separate workloads, not separate users of the same workload.",
        docs_url=DOCS_URL,
    )
