from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.integration import automatic_publishing as rule
from tests.builders import make_catalog_state, make_table_metadata, make_workspace_config


def test_passes_when_on():
    assert (
        rule.check(
            make_workspace_config(automatic_publishing=True),
            make_catalog_state(tables=[make_table_metadata(full_name="main.gold.t")]),
        ).status
        is Status.PASS
    )


def test_passes_when_no_gold():
    assert (
        rule.check(
            make_workspace_config(automatic_publishing=False),
            make_catalog_state(),
        ).status
        is Status.PASS
    )


def test_fails_when_gold_present_and_off():
    assert (
        rule.check(
            make_workspace_config(automatic_publishing=False),
            make_catalog_state(tables=[make_table_metadata(full_name="main.gold.t")]),
        ).status
        is Status.FAIL
    )
