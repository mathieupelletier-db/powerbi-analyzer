from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.report_design import efficient_dax as rule

from tests.builders import make_measure, make_semantic_model


def test_passes_simple_sum():
    m = make_measure(name="Total", expression="SUM(F[r])")
    assert rule.check(make_semantic_model(measures=[m])).status is Status.PASS


def test_fails_nested_filter():
    m = make_measure(
        name="Bad", expression="CALCULATE(SUM(F[r]), FILTER(FILTER(D, D[a]=1), D[b]=2))"
    )
    assert rule.check(make_semantic_model(measures=[m])).status is Status.FAIL


def test_fails_sumx_table_col():
    m = make_measure(name="Bad", expression="SUMX(F, F[r])")
    assert rule.check(make_semantic_model(measures=[m])).status is Status.FAIL
