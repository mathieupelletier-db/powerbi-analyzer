from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import Visual
from powerbi_analyzer.rules.report_design import limit_visuals_per_page as rule
from tests.builders import make_semantic_model


def _v(n):
    return [Visual(page="P", visual_type="card", fields_used=[], filters=[]) for _ in range(n)]


def test_passes_under_limit():
    m = make_semantic_model(visuals_by_page={"P1": _v(8)})
    assert rule.check(m).status is Status.PASS


def test_fails_over_limit():
    m = make_semantic_model(visuals_by_page={"P1": _v(20)})
    f = rule.check(m)
    assert f.status is Status.FAIL
    assert f.evidence["pages"]["P1"] == 20


def test_passes_empty_report():
    # A model with no pages defined should pass.
    assert rule.check(make_semantic_model(visuals_by_page={})).status is Status.PASS
