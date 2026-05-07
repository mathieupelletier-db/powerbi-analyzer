from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.sql_serving import right_size as rule
from tests.builders import make_query, make_warehouse


def test_passes_with_low_memory_no_spill():
    wh = make_warehouse(
        cluster_size="Medium",
        query_history=[make_query(compute_used_mb=1000, spilled_to_disk=False)] * 5,
    )
    assert rule.check(wh).status is Status.PASS


def test_fails_when_spills():
    wh = make_warehouse(
        cluster_size="Medium",
        query_history=[make_query(compute_used_mb=1000, spilled_to_disk=True)],
    )
    assert rule.check(wh).status is Status.FAIL


def test_skips_when_no_pbi_samples():
    wh = make_warehouse(
        query_history=[make_query(client_application="DBeaver", compute_used_mb=10)]
    )
    assert rule.check(wh).status is Status.PASS
