from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.sql_serving import separate_workloads as rule

from tests.builders import make_query, make_warehouse


def test_passes_pure_bi():
    wh = make_warehouse(query_history=[make_query(client_application="Power BI Service")] * 3)
    assert rule.check(wh).status is Status.PASS


def test_fails_mixed_bi_and_etl():
    wh = make_warehouse(
        query_history=[
            make_query(client_application="Power BI Service"),
            make_query(client_application="airflow-scheduler"),
        ]
    )
    assert rule.check(wh).status is Status.FAIL


def test_passes_pure_etl():
    # A warehouse used exclusively for ETL has no BI traffic, so the rule passes.
    wh = make_warehouse(query_history=[make_query(client_application="airflow-scheduler")] * 5)
    assert rule.check(wh).status is Status.PASS
