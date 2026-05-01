from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import WorkspaceConfig
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import rule

RULE_ID = "IN-001"
NAME = "Same region for Power BI and Databricks"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.WARN
APPLIES_TO = ["workspace", "databricks"]
DOCS_URL = "https://learn.microsoft.com/power-bi/admin/service-admin-where-is-my-tenant-located"

REGION_ALIASES = {
    "eastus": {"eastus", "us-east-1", "east-us"},
    "westus": {"westus", "us-west-2"},
    "westeurope": {"westeurope", "eu-west-1"},
}


def _aligned(pbi: str | None, dbx: str) -> bool:
    if not pbi:
        return True
    pbi_l = pbi.lower().replace(" ", "")
    dbx_l = dbx.lower()
    for aliases in REGION_ALIASES.values():
        if pbi_l in aliases and dbx_l in aliases:
            return True
    return pbi_l == dbx_l


@rule(RULE_ID)
def check(config: WorkspaceConfig, warehouse: WarehouseState) -> Finding:
    if _aligned(config.capacity_region, warehouse.region):
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=warehouse.name,
            summary=f"PBI {config.capacity_region} ↔ Databricks {warehouse.region}.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=warehouse.name,
        severity=SEVERITY,
        summary=f"PBI region {config.capacity_region} != Databricks region {warehouse.region}.",
        evidence={"pbi_region": config.capacity_region, "databricks_region": warehouse.region},
        why="Cross-region traffic adds latency and possibly egress cost.",
        fix="Co-locate the Power BI capacity (or Premium) with the Databricks workspace.",
        docs_url=DOCS_URL,
    )
