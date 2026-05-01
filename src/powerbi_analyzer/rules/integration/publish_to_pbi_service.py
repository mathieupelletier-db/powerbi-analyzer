from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import WorkspaceConfig
from powerbi_analyzer.rules import rule

RULE_ID = "IN-010"
NAME = "Use Publish to Power BI Service from Databricks"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.INFO
APPLIES_TO = ["workspace", "databricks"]
DOCS_URL = "https://docs.databricks.com/integrations/configure-power-bi-online-service.html"


@rule(RULE_ID)
def check(config: WorkspaceConfig, catalog: CatalogState) -> Finding:
    if config.publish_to_pbi_service:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=config.workspace_id,
            summary="Publish to Power BI Service in use.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=config.workspace_id,
        severity=SEVERITY,
        summary="Publish to Power BI Service not enabled.",
        evidence={
            "gold_tables_visible": [t.full_name for t in catalog.tables if t.layer == "gold"][:5]
        },
        why="Publish-from-UC keeps the semantic model in sync with Gold without manual refresh.",
        fix="Enable Publish to Power BI Service from the Unity Catalog table page.",
        docs_url=DOCS_URL,
    )
