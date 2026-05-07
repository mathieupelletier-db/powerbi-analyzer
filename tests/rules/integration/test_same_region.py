from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.integration import same_region as rule
from tests.builders import make_warehouse, make_workspace_config


def test_passes_aliased_regions():
    cfg = make_workspace_config(capacity_region="eastus")
    wh = make_warehouse(region="us-east-1")
    assert rule.check(cfg, wh).status is Status.PASS


def test_fails_different_regions():
    cfg = make_workspace_config(capacity_region="eastus")
    wh = make_warehouse(region="us-west-2")
    assert rule.check(cfg, wh).status is Status.FAIL


def test_passes_when_pbi_region_unknown():
    cfg = make_workspace_config(capacity_region=None)
    assert rule.check(cfg, make_warehouse()).status is Status.PASS
