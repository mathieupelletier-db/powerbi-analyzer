from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import StorageMode
from powerbi_analyzer.rules.integration import dq_for_fact_dual_for_dim as rule
from tests.builders import make_semantic_model, make_table


def test_passes_proper_modes():
    fact = make_table(
        name="Fact_Sales", storage_mode=StorageMode.DIRECT_QUERY, row_count=10_000_000
    )
    dim = make_table(name="Dim_Customer", storage_mode=StorageMode.DUAL, row_count=10_000)
    assert rule.check(make_semantic_model(tables=[fact, dim])).status is Status.PASS


def test_fails_fact_in_import():
    fact = make_table(name="Fact_Sales", storage_mode=StorageMode.IMPORT, row_count=10_000_000)
    assert rule.check(make_semantic_model(tables=[fact])).status is Status.FAIL


def test_fails_dim_not_dual():
    dim = make_table(name="Dim_Customer", storage_mode=StorageMode.IMPORT, row_count=10_000)
    assert rule.check(make_semantic_model(tables=[dim])).status is Status.FAIL
