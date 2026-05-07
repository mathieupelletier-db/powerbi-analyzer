from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.sql_serving import configure_scaling as rule
from tests.builders import make_query, make_warehouse


def test_passes_when_max_clusters_above_one():
    assert rule.check(make_warehouse(max_clusters=4)).status is Status.PASS


def test_passes_when_max_one_but_no_queueing():
    wh = make_warehouse(max_clusters=1, query_history=[make_query(queue_duration_ms=0)])
    assert rule.check(wh).status is Status.PASS


def test_fails_when_max_one_and_queueing():
    wh = make_warehouse(max_clusters=1, query_history=[make_query(queue_duration_ms=2000)])
    assert rule.check(wh).status is Status.FAIL
