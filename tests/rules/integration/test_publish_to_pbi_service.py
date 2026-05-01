from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.integration import publish_to_pbi_service as rule

from tests.builders import make_catalog_state, make_workspace_config


def test_passes():
    assert (
        rule.check(make_workspace_config(publish_to_pbi_service=True), make_catalog_state()).status
        is Status.PASS
    )


def test_fails():
    assert (
        rule.check(make_workspace_config(publish_to_pbi_service=False), make_catalog_state()).status
        is Status.FAIL
    )
