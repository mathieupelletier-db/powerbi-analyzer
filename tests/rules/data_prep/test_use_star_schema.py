from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.data_prep import use_star_schema as rule

from tests.builders import (
    make_catalog_state,
    make_foreign_key,
    make_table_metadata,
    make_warehouse,
)


def test_passes_no_dim_to_dim():
    cat = make_catalog_state(
        tables=[
            make_table_metadata(full_name="main.gold.fact_sales", layer="gold"),
            make_table_metadata(full_name="main.gold.dim_customer", layer="gold"),
        ]
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS


def test_fails_dim_to_dim():
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.dim_customer",
                layer="gold",
                foreign_keys=[make_foreign_key(to_table="main.gold.dim_region")],
            ),
            make_table_metadata(full_name="main.gold.dim_region", layer="gold"),
        ]
    )
    assert rule.check(cat, make_warehouse()).status is Status.FAIL


def test_passes_fact_to_dim():
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.fact_orders",
                layer="gold",
                foreign_keys=[make_foreign_key(to_table="main.gold.dim_customer")],
            ),
            make_table_metadata(full_name="main.gold.dim_customer", layer="gold"),
        ]
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS
