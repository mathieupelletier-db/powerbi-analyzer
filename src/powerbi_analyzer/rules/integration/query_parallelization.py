from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import WorkspaceConfig
from powerbi_analyzer.rules import rule

RULE_ID = "IN-006"
NAME = "Tune Power BI query parallelization"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.WARN
APPLIES_TO = ["workspace"]
DOCS_URL = "https://learn.microsoft.com/power-bi/transform-model/desktop-storage-mode"


@rule(RULE_ID)
def check(config: WorkspaceConfig) -> Finding:
    p = config.parallelism
    issues = []
    if p.max_parallelism_per_query in (None, 1):
        issues.append(f"MaxParallelismPerQuery={p.max_parallelism_per_query}")
    if p.max_simultaneous_evaluations is not None and p.max_simultaneous_evaluations < 6:
        issues.append(f"MaxSimultaneousEvaluations={p.max_simultaneous_evaluations}")
    if not issues:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=config.workspace_id,
            summary="Parallelism settings appear tuned.",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=config.workspace_id,
        severity=SEVERITY,
        summary="Parallelism settings at low/default values.",
        evidence={"settings": issues},
        why="Default parallelism caps PBI's ability to parallelize across visuals and workers.",
        fix="Increase MaxParallelismPerQuery to 10+ and MaxSimultaneousEvaluations to 6+.",
        docs_url=DOCS_URL,
    )
