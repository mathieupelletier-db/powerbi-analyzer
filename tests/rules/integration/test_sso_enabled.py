from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.integration import sso_enabled as rule

from tests.builders import make_workspace_config


def test_passes():
    assert rule.check(make_workspace_config(sso_enabled=True)).status is Status.PASS


def test_fails():
    assert rule.check(make_workspace_config(sso_enabled=False)).status is Status.FAIL
