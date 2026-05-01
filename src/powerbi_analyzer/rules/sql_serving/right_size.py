from statistics import mean

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "SS-004"
NAME = "Right-size warehouse for dataset"
PHASE = Phase.SQL_SERVING
SEVERITY = Severity.INFO
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/admin/sql-endpoints.html#sizes"

_SIZE_MEMORY_GB = {
    "2X-Small": 64,
    "X-Small": 128,
    "Small": 256,
    "Medium": 512,
    "Large": 1024,
    "X-Large": 2048,
    "2X-Large": 4096,
    "3X-Large": 8192,
    "4X-Large": 12288,
}


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    pbi = [
        q
        for q in warehouse.query_history
        if (q.client_application or "").lower().startswith("power bi")
        and q.compute_used_mb is not None
    ]
    if not pbi:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="No Power BI compute samples — cannot evaluate sizing.",
            docs_url=DOCS_URL,
        )
    compute_samples: list[int] = [q.compute_used_mb for q in pbi if q.compute_used_mb is not None]
    avg_mb = mean(compute_samples)
    spilled = sum(1 for q in pbi if q.spilled_to_disk)
    cap_mb = _SIZE_MEMORY_GB.get(warehouse.cluster_size, 512) * 1024
    if avg_mb < 0.6 * cap_mb and spilled == 0:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary=f"Avg {avg_mb:.0f} MB << capacity {cap_mb} MB; no spills.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=(
            f"Warehouse '{warehouse.cluster_size}' may be undersized "
            f"(avg {avg_mb:.0f} MB; {spilled} spill(s))."
        ),
        evidence={
            "avg_compute_mb": round(avg_mb),
            "spilled_query_count": spilled,
            "cluster_size": warehouse.cluster_size,
            "capacity_mb": cap_mb,
        },
        why="Spills and sustained near-cap memory indicate the warehouse is under-provisioned for the dataset.",
        fix="Increase cluster_size by one tier and re-evaluate, or reduce concurrent load.",
        docs_url=DOCS_URL,
    )
