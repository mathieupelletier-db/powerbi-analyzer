from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import QueryReductionConfig, Visual
from powerbi_analyzer.rules.report_design import query_reduction_settings as rule

from tests.builders import make_semantic_model


def _slicers(n):
    return [Visual(page="P", visual_type="slicer", fields_used=[], filters=[]) for _ in range(n)]


def test_passes_few_slicers():
    m = make_semantic_model(visuals_by_page={"P1": _slicers(2)})
    assert rule.check(m).status is Status.PASS


def test_fails_many_slicers_no_apply():
    m = make_semantic_model(visuals_by_page={"P1": _slicers(5)})
    assert rule.check(m).status is Status.FAIL


def test_passes_many_slicers_with_apply():
    m = make_semantic_model(
        visuals_by_page={"P1": _slicers(5)},
        query_reduction_settings=QueryReductionConfig(apply_all_slicers_button=True),
    )
    assert rule.check(m).status is Status.PASS
