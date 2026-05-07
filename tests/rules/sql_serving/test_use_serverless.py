from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.sql_serving import use_serverless as rule
from tests.builders import make_warehouse


def test_passes_serverless():
    assert rule.check(make_warehouse(type="serverless")).status is Status.PASS


def test_fails_pro():
    f = rule.check(make_warehouse(type="pro"))
    assert f.status is Status.FAIL
    assert "pro" in f.evidence["warehouse_type"].lower()


def test_fails_classic():
    f = rule.check(make_warehouse(type="classic"))
    assert f.status is Status.FAIL
