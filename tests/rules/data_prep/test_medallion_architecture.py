from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.data_prep import medallion_architecture as rule

from tests.builders import make_catalog_state, make_table_metadata, make_warehouse


def test_passes_when_pbi_only_hits_gold():
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.fact_sales", layer="gold")],
        referenced_by_powerbi=["main.gold.fact_sales"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS


def test_fails_when_pbi_hits_staging():
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.staging.orders", layer="unknown")],
        referenced_by_powerbi=["main.staging.orders"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.FAIL


def test_passes_when_pbi_references_unknown_table():
    cat = make_catalog_state(referenced_by_powerbi=["main.gold.something_not_listed"])
    assert rule.check(cat, make_warehouse()).status is Status.PASS
