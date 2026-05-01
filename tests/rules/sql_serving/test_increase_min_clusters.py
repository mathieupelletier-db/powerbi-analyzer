from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.sql_serving import increase_min_clusters as rule

from tests.builders import make_query, make_warehouse


def test_passes_when_min_above_one():
    assert rule.check(make_warehouse(min_clusters=2)).status is Status.PASS


def test_passes_when_no_long_waits():
    wh = make_warehouse(min_clusters=1, query_history=[make_query(queue_duration_ms=100)])
    assert rule.check(wh).status is Status.PASS


def test_fails_when_long_waits_and_min_one():
    wh = make_warehouse(min_clusters=1, query_history=[make_query(queue_duration_ms=10000)])
    assert rule.check(wh).status is Status.FAIL
