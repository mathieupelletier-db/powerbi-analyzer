from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import GatewayConfig
from powerbi_analyzer.rules.integration import gateway_clusters as rule
from tests.builders import make_workspace_config


def test_passes_no_gateway():
    assert rule.check(make_workspace_config(gateway=None)).status is Status.PASS


def test_passes_clustered():
    cfg = make_workspace_config(gateway=GatewayConfig(name="gw", cluster_size=2))
    assert rule.check(cfg).status is Status.PASS


def test_fails_single_node():
    cfg = make_workspace_config(gateway=GatewayConfig(name="gw", cluster_size=1))
    assert rule.check(cfg).status is Status.FAIL
