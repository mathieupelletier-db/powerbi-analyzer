from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.sql_serving import enable_auto_stop as rule
from tests.builders import make_warehouse


def test_passes_when_auto_stop_set_low():
    assert rule.check(make_warehouse(auto_stop_mins=10)).status is Status.PASS


def test_fails_when_auto_stop_zero():
    assert rule.check(make_warehouse(auto_stop_mins=0)).status is Status.FAIL


def test_fails_when_auto_stop_too_high():
    f = rule.check(make_warehouse(auto_stop_mins=120))
    assert f.status is Status.FAIL
    assert "120" in f.summary


def test_fails_when_null():
    assert rule.check(make_warehouse(auto_stop_mins=None)).status is Status.FAIL
