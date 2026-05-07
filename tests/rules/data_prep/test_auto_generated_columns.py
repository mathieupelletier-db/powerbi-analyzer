from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.data_prep import auto_generated_columns as rule
from tests.builders import make_query, make_warehouse


def test_passes_no_pbi_history():
    assert rule.check(make_warehouse()).status is Status.PASS


def test_passes_few_repeats():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Service", referenced_tables=["main.gold.fact_sales"]
            )
            for _ in range(3)
        ]
    )
    assert rule.check(wh).status is Status.PASS


def test_fails_when_pattern_repeated_5_times():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Service", referenced_tables=["main.gold.fact_sales"]
            )
            for _ in range(5)
        ]
    )
    f = rule.check(wh)
    assert f.status is Status.FAIL
    assert f.evidence["repeated_pattern_count"] == 1


def test_fails_counts_multiple_patterns():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Desktop", referenced_tables=["main.gold.fact_sales"]
            )
            for _ in range(6)
        ]
        + [
            make_query(
                client_application="Power BI Desktop", referenced_tables=["main.gold.dim_customer"]
            )
            for _ in range(5)
        ]
    )
    f = rule.check(wh)
    assert f.status is Status.FAIL
    assert f.evidence["repeated_pattern_count"] == 2
