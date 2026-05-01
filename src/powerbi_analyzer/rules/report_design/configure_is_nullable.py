from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules import rule

RULE_ID = "RD-007"
NAME = "Configure 'Is nullable' to match source"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.INFO
APPLIES_TO = ["pbix", "pbip", "workspace", "databricks"]
DOCS_URL = "https://learn.microsoft.com/power-bi/transform-model/desktop-tutorial-create-calculated-columns"


@rule(RULE_ID)
def check(model: SemanticModel, catalog: CatalogState) -> Finding:
    src_nn: dict[tuple[str, str], bool] = {}
    for cat_tbl in catalog.tables:
        short = cat_tbl.full_name.split(".")[-1].lower()
        for cat_col in cat_tbl.columns:
            src_nn[(short, cat_col.name.lower())] = not cat_col.is_nullable
    mismatches: list[str] = []
    for mdl_tbl in model.tables:
        for mdl_col in mdl_tbl.columns:
            key = (mdl_tbl.name.lower(), mdl_col.name.lower())
            if mdl_col.is_nullable and src_nn.get(key, False):
                mismatches.append(f"{mdl_tbl.name}[{mdl_col.name}]")
    if not mismatches:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="All columns' nullability matches source.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(mismatches)} column(s) marked nullable but source is NOT NULL.",
        evidence={"columns": mismatches},
        why="Nullable=true blocks Power BI from generating simpler SQL (e.g., INNER JOIN).",
        fix="Set IsNullable=false on these columns in the semantic model.",
        docs_url=DOCS_URL,
    )
