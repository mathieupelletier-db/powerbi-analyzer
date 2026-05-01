from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.sql_serving import monitor_system_tables as rule

from tests.builders import make_warehouse, make_warehouse_event


def test_passes_when_no_events():
    assert rule.check(make_warehouse()).status is Status.PASS


def test_passes_when_events_and_scaling_configured():
    wh = make_warehouse(
        min_clusters=2, max_clusters=4, events=[make_warehouse_event(event_type="SCALED_UP")]
    )
    assert rule.check(wh).status is Status.PASS


def test_fails_when_events_but_scaling_off():
    wh = make_warehouse(
        min_clusters=1, max_clusters=1, events=[make_warehouse_event(event_type="SCALED_UP")]
    )
    assert rule.check(wh).status is Status.FAIL
