from powerbi_analyzer.domain.finding import Severity, Status
from powerbi_analyzer.rules.sql_serving import use_sql_warehouse as rule

from tests.builders import make_query, make_warehouse


def test_passes_when_no_pbi_queries_on_clusters():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Desktop",
                warehouse_id="wh",
                all_purpose_cluster_id=None,
            ),
        ]
    )
    assert rule.check(wh).status is Status.PASS


def test_fails_when_pbi_query_runs_on_all_purpose_cluster():
    wh = make_warehouse(
        query_history=[
            make_query(
                client_application="Power BI Service",
                warehouse_id=None,
                all_purpose_cluster_id="cluster-XYZ",
            ),
        ]
    )
    f = rule.check(wh)
    assert f.status is Status.FAIL
    assert f.severity is Severity.ERROR
    assert "cluster-XYZ" in f.evidence["clusters"][0]


def test_passes_when_no_pbi_queries():
    wh = make_warehouse(
        query_history=[
            make_query(client_application="DBeaver"),
        ]
    )
    assert rule.check(wh).status is Status.PASS
