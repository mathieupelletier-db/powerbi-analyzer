from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.data_prep import persisted_aggregates as rule
from tests.builders import make_query, make_warehouse


def test_passes_no_pbi():
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


def test_fails_when_repeated_set():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Service", referenced_tables=["main.gold.fact_sales"]
            )
            for _ in range(6)
        ]
    )
    assert rule.check(wh).status is Status.FAIL
