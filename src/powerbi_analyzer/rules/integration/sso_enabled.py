from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import WorkspaceConfig
from powerbi_analyzer.rules import rule

RULE_ID = "IN-007"
NAME = "Enable SSO between Power BI and Databricks"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.ERROR
APPLIES_TO = ["workspace"]
DOCS_URL = "https://docs.databricks.com/integrations/configure-power-bi-sso.html"


@rule(RULE_ID)
def check(config: WorkspaceConfig) -> Finding:
    if config.sso_enabled:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=config.workspace_id,
            summary="SSO is enabled.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=config.workspace_id,
        severity=SEVERITY,
        summary="SSO between Power BI and Databricks is disabled.",
        evidence={},
        why="Without SSO, Unity Catalog access controls do not flow through to Power BI users.",
        fix="Enable SSO on the dataset's data source in Power BI Service.",
        docs_url=DOCS_URL,
    )
