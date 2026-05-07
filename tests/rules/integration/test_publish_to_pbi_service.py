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


def test_fail_evidence_lists_gold_tables():
    from tests.builders import make_table_metadata

    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.dim_customer", layer="gold")]
    )
    f = rule.check(make_workspace_config(publish_to_pbi_service=False), cat)
    assert f.status is Status.FAIL
    assert "main.gold.dim_customer" in f.evidence["gold_tables_visible"]
