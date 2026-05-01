from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules import rule

RULE_ID = "RD-010"
NAME = "Add Apply All Slicers when many slicers"
PHASE = Phase.REPORT_DESIGN
SEVERITY = Severity.INFO
APPLIES_TO = ["pbix", "pbip", "workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/create-reports/desktop-query-reduction"

SLICER_THRESHOLD = 3


@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    slicer_pages: dict[str, int] = {}
    for page, visuals in model.visuals_by_page.items():
        slicers = sum(1 for v in visuals if v.visual_type.lower() == "slicer")
        if slicers > SLICER_THRESHOLD:
            slicer_pages[page] = slicers
    cfg = model.query_reduction_settings
    if not slicer_pages or (cfg and cfg.apply_all_slicers_button):
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=model.name,
            summary="No slicer-heavy pages, or Apply All Slicers enabled.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=model.name,
        severity=SEVERITY,
        summary=f"{len(slicer_pages)} page(s) with > {SLICER_THRESHOLD} slicers and no Apply All Slicers button.",
        evidence={"pages": slicer_pages},
        why="Each slicer change re-runs visuals; Apply All Slicers batches changes.",
        fix="In the Power BI report options, enable 'Add an Apply button to each slicer'.",
        docs_url=DOCS_URL,
    )
