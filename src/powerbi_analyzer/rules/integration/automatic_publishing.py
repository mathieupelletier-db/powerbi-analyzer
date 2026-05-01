from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import WorkspaceConfig
from powerbi_analyzer.rules import rule

RULE_ID = "IN-011"
NAME = "Use Automatic Publishing from Unity Catalog"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.INFO
APPLIES_TO = ["workspace", "databricks"]
DOCS_URL = "https://docs.databricks.com/integrations/configure-power-bi-online-service.html"


@rule(RULE_ID)
def check(config: WorkspaceConfig, catalog: CatalogState) -> Finding:
    gold = [t.full_name for t in catalog.tables if t.layer == "gold"]
    if config.automatic_publishing or not gold:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=config.workspace_id,
            summary="Automatic Publishing on or no Gold tables.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=config.workspace_id,
        severity=SEVERITY,
        summary=f"{len(gold)} Gold table(s) not enrolled in Automatic Publishing.",
        evidence={"gold_tables_sample": gold[:5]},
        why="Automatic Publishing pushes UC schema changes to Power BI without manual intervention.",
        fix="Enable Automatic Publishing on the Gold catalog/schema.",
        docs_url=DOCS_URL,
    )
