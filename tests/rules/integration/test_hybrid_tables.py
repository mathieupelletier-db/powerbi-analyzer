from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import StorageMode
from powerbi_analyzer.rules.integration import hybrid_tables as rule
from tests.builders import make_semantic_model, make_table


def test_passes_small():
    t = make_table(name="F", storage_mode=StorageMode.DIRECT_QUERY, row_count=1000)
    assert rule.check(make_semantic_model(tables=[t])).status is Status.PASS


def test_fails_large_dq_no_hybrid():
    t = make_table(name="F", storage_mode=StorageMode.DIRECT_QUERY, row_count=200_000_000)
    assert rule.check(make_semantic_model(tables=[t])).status is Status.FAIL


def test_passes_large_import_table():
    # Import tables are not candidate for hybrid — rule only targets DirectQuery.
    t = make_table(name="F", storage_mode=StorageMode.IMPORT, row_count=200_000_000)
    assert rule.check(make_semantic_model(tables=[t])).status is Status.PASS
