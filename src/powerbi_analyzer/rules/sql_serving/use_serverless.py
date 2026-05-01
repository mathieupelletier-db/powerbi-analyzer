from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "SS-002"
NAME = "Use Serverless SQL warehouse"
PHASE = Phase.SQL_SERVING
SEVERITY = Severity.WARN
APPLIES_TO = ["databricks"]
DOCS_URL = "https://docs.databricks.com/sql/admin/serverless.html"


@rule(RULE_ID)
def check(warehouse: WarehouseState) -> Finding:
    if warehouse.type == "serverless":
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary="Warehouse is Serverless.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"Warehouse type is '{warehouse.type}', not Serverless.",
        evidence={"warehouse_type": warehouse.type},
        why="Serverless gives instant elasticity, better price/performance, and shared query result cache that survives restarts.",
        fix="If your tenant supports it, switch the warehouse to Serverless.",
        docs_url=DOCS_URL,
    )
