from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import StorageMode
from powerbi_analyzer.rules.report_design import automatic_aggregations as rule
from tests.builders import make_semantic_model, make_table


def test_passes_when_no_dq():
    assert rule.check(make_semantic_model()).status is Status.PASS


def test_fails_dq_without_agg():
    t = make_table(name="F", storage_mode=StorageMode.DIRECT_QUERY)
    assert rule.check(make_semantic_model(tables=[t])).status is Status.FAIL


def test_passes_when_agg_table_present():
    fact = make_table(name="F", storage_mode=StorageMode.DIRECT_QUERY)
    agg = make_table(name="F_agg", storage_mode=StorageMode.IMPORT, is_aggregation_table=True)
    assert rule.check(make_semantic_model(tables=[fact, agg])).status is Status.PASS
