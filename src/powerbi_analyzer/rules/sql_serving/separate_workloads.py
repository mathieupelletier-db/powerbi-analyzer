from collections import Counter

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "SS-008"
NAME = "Separate warehouses for different workloads"
PHASE = Phase.SQL_SERVING
SEVERITY = Severity.INFO
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/admin/sql-endpoints.html"


def _bucket(app: str | None) -> str:
    a = (app or "").lower()
    if "power bi" in a or "tableau" in a or ("dbt" in a and "ide" in a):
        return "bi"
    if "etl" in a or "airflow" in a or "dbt" in a or "jobs" in a:
        return "etl"
    return "other"


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    counts = Counter(_bucket(q.client_application) for q in warehouse.query_history)
    bi = counts.get("bi", 0)
    etl = counts.get("etl", 0)
    if bi == 0 or etl == 0:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary=f"BI={bi} ETL={etl}; not mixed.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"Warehouse runs both BI ({bi}) and ETL ({etl}) workloads.",
        evidence=dict(counts),
        why="Mixing interactive BI and bulk ETL on one warehouse causes BI latency spikes during ETL.",
        fix="Create a dedicated SQL warehouse for ETL, leave this one for BI.",
        docs_url=DOCS_URL,
    )
