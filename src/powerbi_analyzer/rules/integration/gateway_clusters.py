from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.domain.semantic_model import WorkspaceConfig
from powerbi_analyzer.rules import rule

RULE_ID = "IN-009"
NAME = "Use clustered gateways"
PHASE = Phase.INTEGRATION
SEVERITY = Severity.INFO
APPLIES_TO = ["workspace"]
DOCS_URL = "https://learn.microsoft.com/data-integration/gateway/service-gateway-high-availability-clusters"


@rule(RULE_ID)
def check(config: WorkspaceConfig) -> Finding:
    g = config.gateway
    if g is None:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=config.workspace_id,
            summary="No gateway in use.",
            docs_url=DOCS_URL,
        )
    if g.cluster_size > 1:
        return Finding.passed(
            RULE_ID,
            NAME,
            phase=PHASE,
            target=config.workspace_id,
            summary=f"Gateway clustered ({g.cluster_size} nodes).",
            docs_url=DOCS_URL,
        )
    return Finding.failed(
        RULE_ID,
        NAME,
        phase=PHASE,
        target=config.workspace_id,
        severity=SEVERITY,
        summary="Gateway is single-node.",
        evidence={"gateway_name": g.name, "cluster_size": g.cluster_size},
        why="Single-node gateway is a SPOF and bottleneck for refresh.",
        fix="Cluster the gateway with ≥ 2 nodes.",
        docs_url=DOCS_URL,
    )
