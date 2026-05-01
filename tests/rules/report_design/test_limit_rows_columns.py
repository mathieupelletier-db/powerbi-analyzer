from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import StorageMode
from powerbi_analyzer.rules.report_design import limit_rows_columns as rule

from tests.builders import make_column, make_semantic_model, make_table


def test_passes_narrow():
    t = make_table(
        name="T",
        storage_mode=StorageMode.DIRECT_QUERY,
        columns=[make_column(name=f"c{i}") for i in range(10)],
    )
    assert rule.check(make_semantic_model(tables=[t])).status is Status.PASS


def test_fails_wide_dq():
    t = make_table(
        name="T",
        storage_mode=StorageMode.DIRECT_QUERY,
        columns=[make_column(name=f"c{i}") for i in range(60)],
    )
    assert rule.check(make_semantic_model(tables=[t])).status is Status.FAIL


def test_passes_wide_import_table():
    t = make_table(
        name="T",
        storage_mode=StorageMode.IMPORT,
        columns=[make_column(name=f"c{i}") for i in range(60)],
    )
    assert rule.check(make_semantic_model(tables=[t])).status is Status.PASS
