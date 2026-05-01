from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.data_prep import compute_statistics as rule

from tests.builders import make_catalog_state, make_table_metadata, make_warehouse


def test_passes_when_all_have_stats():
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.t", has_column_stats=True)],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS


def test_fails_when_missing_stats():
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.t", has_column_stats=False)],
        referenced_by_powerbi=["main.gold.t"],
    )
    f = rule.check(cat, make_warehouse())
    assert f.status is Status.FAIL
    assert "main.gold.t" in f.evidence["tables"]


def test_passes_when_no_referenced_tables():
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.t", has_column_stats=False)],
        referenced_by_powerbi=[],
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS


def test_fails_lists_all_missing_stats():
    cat = make_catalog_state(
        tables=[
            make_table_metadata(full_name="main.gold.a", has_column_stats=False),
            make_table_metadata(full_name="main.gold.b", has_column_stats=False),
            make_table_metadata(full_name="main.gold.c", has_column_stats=True),
        ],
        referenced_by_powerbi=["main.gold.a", "main.gold.b", "main.gold.c"],
    )
    f = rule.check(cat, make_warehouse())
    assert f.status is Status.FAIL
    assert f.evidence["tables"] == ["main.gold.a", "main.gold.b"]
