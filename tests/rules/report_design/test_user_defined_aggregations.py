from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import StorageMode
from powerbi_analyzer.rules.report_design import user_defined_aggregations as rule

from tests.builders import make_semantic_model, make_table


def test_passes_when_small():
    t = make_table(name="F", storage_mode=StorageMode.DIRECT_QUERY, row_count=1_000)
    assert rule.check(make_semantic_model(tables=[t])).status is Status.PASS


def test_fails_large_dq_no_agg():
    t = make_table(name="F", storage_mode=StorageMode.DIRECT_QUERY, row_count=200_000_000)
    assert rule.check(make_semantic_model(tables=[t])).status is Status.FAIL


def test_passes_when_agg_exists():
    fact = make_table(name="F", storage_mode=StorageMode.DIRECT_QUERY, row_count=200_000_000)
    agg = make_table(
        name="F_agg", storage_mode=StorageMode.IMPORT, row_count=10_000, is_aggregation_table=True
    )
    assert rule.check(make_semantic_model(tables=[fact, agg])).status is Status.PASS
