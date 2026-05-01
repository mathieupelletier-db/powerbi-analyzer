from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.sql_serving import same_warehouse_per_dataset as rule

from tests.builders import make_query, make_warehouse


def test_passes_when_single_warehouse():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Service",
                warehouse_id="wh-1",
                referenced_tables=["main.gold.fact_sales"],
            ),
        ]
    )
    assert rule.check(wh).status is Status.PASS


def test_fails_when_table_seen_on_multiple_warehouses():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Service",
                warehouse_id="wh-1",
                referenced_tables=["main.gold.fact_sales"],
            ),
            make_query(
                client_application="Power BI Service",
                warehouse_id="wh-2",
                referenced_tables=["main.gold.fact_sales"],
            ),
        ]
    )
    f = rule.check(wh)
    assert f.status is Status.FAIL
    assert "main.gold.fact_sales" in f.evidence["tables"]
