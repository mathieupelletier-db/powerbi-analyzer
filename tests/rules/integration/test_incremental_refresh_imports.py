from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import Partition, RefreshPolicy, StorageMode
from powerbi_analyzer.rules.integration import incremental_refresh_imports as rule
from tests.builders import make_semantic_model, make_table


def test_passes_small():
    t = make_table(name="T", storage_mode=StorageMode.IMPORT, row_count=10_000)
    assert rule.check(make_semantic_model(tables=[t])).status is Status.PASS


def test_fails_large_no_policy():
    t = make_table(name="T", storage_mode=StorageMode.IMPORT, row_count=10_000_000)
    assert rule.check(make_semantic_model(tables=[t])).status is Status.FAIL


def test_passes_large_with_policy():
    rp = RefreshPolicy(
        rolling_window_unit="year",
        rolling_window_size=3,
        incremental_unit="day",
        incremental_size=7,
    )
    p = Partition(name="P", source_type="m", source_expression="...", refresh_policy=rp)
    t = make_table(name="T", storage_mode=StorageMode.IMPORT, row_count=10_000_000, partitions=[p])
    assert rule.check(make_semantic_model(tables=[t])).status is Status.PASS
