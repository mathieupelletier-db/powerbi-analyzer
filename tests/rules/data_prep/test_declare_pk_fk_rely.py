from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.data_prep import declare_pk_fk_rely as rule

from tests.builders import make_catalog_state, make_table_metadata, make_warehouse


def test_passes_when_all_have_pk_rely():
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.t", primary_key=["id"], rely=True)],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS


def test_fails_when_missing_pk():
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.t", primary_key=None, rely=False)],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.FAIL


def test_fails_when_pk_without_rely():
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.t", primary_key=["id"], rely=False)],
        referenced_by_powerbi=["main.gold.t"],
    )
    f = rule.check(cat, make_warehouse())
    assert f.status is Status.FAIL
    assert "main.gold.t" in f.evidence["pk_without_rely"]
