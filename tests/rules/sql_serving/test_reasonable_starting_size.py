from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.sql_serving import reasonable_starting_size as rule
from tests.builders import make_query, make_warehouse


def test_passes_for_medium():
    assert rule.check(make_warehouse(cluster_size="Medium")).status is Status.PASS


def test_passes_for_2xsmall_when_idle():
    assert rule.check(make_warehouse(cluster_size="2X-Small")).status is Status.PASS


def test_fails_for_2xsmall_with_queueing():
    wh = make_warehouse(cluster_size="2X-Small", query_history=[make_query(queue_duration_ms=2000)])
    assert rule.check(wh).status is Status.FAIL
