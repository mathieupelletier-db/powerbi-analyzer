from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "SS-003"
NAME = "Enable SQL warehouse Auto stop"
PHASE = Phase.SQL_SERVING
SEVERITY = Severity.WARN
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/admin/sql-endpoints.html#auto-stop"


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    mins = warehouse.auto_stop_mins
    if mins is not None and 1 <= mins <= 60:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary=f"Auto stop set to {mins} minutes.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"Auto stop is {mins!r}, expected 1-60 minutes.",
        evidence={"auto_stop_mins": mins},
        why="When idle, the warehouse continues to bill compute. Serverless takes 5-10s to resume.",
        fix="Set auto_stop_mins to 10 for interactive Power BI workloads, or 30 if you accept warmer cache.",
        docs_url=DOCS_URL,
    )
