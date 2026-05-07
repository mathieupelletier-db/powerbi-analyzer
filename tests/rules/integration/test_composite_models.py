from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import StorageMode
from powerbi_analyzer.rules.integration import composite_models as rule
from tests.builders import make_semantic_model, make_table


def test_passes_when_mixed():
    m = make_semantic_model(
        tables=[
            make_table(name="A", storage_mode=StorageMode.IMPORT),
            make_table(name="B", storage_mode=StorageMode.DIRECT_QUERY),
        ]
    )
    assert rule.check(m).status is Status.PASS


def test_fails_when_single_mode():
    m = make_semantic_model(
        tables=[
            make_table(name="A", storage_mode=StorageMode.IMPORT),
            make_table(name="B", storage_mode=StorageMode.IMPORT),
        ]
    )
    assert rule.check(m).status is Status.FAIL


def test_passes_when_no_tables():
    # An empty model has nothing to recommend, so the rule passes trivially.
    assert rule.check(make_semantic_model(tables=[])).status is Status.PASS
