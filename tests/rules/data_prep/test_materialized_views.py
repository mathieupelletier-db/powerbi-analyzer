from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.data_prep import materialized_views as rule
from tests.builders import make_query, make_warehouse


def test_passes_no_pbi_history():
    assert rule.check(make_warehouse()).status is Status.PASS


def test_passes_few_repeats():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Service", referenced_tables=["main.gold.fact_sales"]
            )
            for _ in range(2)
        ]
    )
    assert rule.check(wh).status is Status.PASS


def test_fails_when_pattern_repeated_3_times():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Service", referenced_tables=["main.gold.fact_sales"]
            )
            for _ in range(3)
        ]
    )
    f = rule.check(wh)
    assert f.status is Status.FAIL
    assert "main.gold.fact_sales" in f.evidence["candidates"]


def test_fails_counts_multiple_candidates():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Desktop", referenced_tables=["main.gold.fact_sales"]
            )
            for _ in range(4)
        ]
        + [
            make_query(
                client_application="Power BI Desktop", referenced_tables=["main.gold.dim_customer"]
            )
            for _ in range(3)
        ]
    )
    f = rule.check(wh)
    assert f.status is Status.FAIL
    assert len(f.evidence["candidates"]) == 2
