from powerbi_analyzer.domain.semantic_model import StorageMode

from tests.builders import (
    make_catalog_state,
    make_column,
    make_relationship,
    make_semantic_model,
    make_table,
    make_table_metadata,
    make_warehouse,
)


def test_make_semantic_model_defaults_are_valid():
    m = make_semantic_model()
    assert m.source == "pbix"
    assert m.tables == []


def test_make_semantic_model_overrides():
    m = make_semantic_model(name="X", tables=[make_table(name="T")])
    assert m.name == "X"
    assert m.tables[0].name == "T"


def test_make_table_with_columns():
    t = make_table(
        name="Fact",
        columns=[make_column(name="id", is_key=True)],
        storage_mode=StorageMode.DIRECT_QUERY,
    )
    assert t.columns[0].is_key is True
    assert t.storage_mode is StorageMode.DIRECT_QUERY


def test_make_relationship_default():
    r = make_relationship()
    assert r.cardinality == "one-to-many"


def test_make_warehouse_default_serverless():
    w = make_warehouse()
    assert w.type == "serverless"


def test_make_table_metadata_defaults():
    t = make_table_metadata(full_name="main.gold.t")
    assert t.layer == "gold"
    assert t.clustering.kind == "liquid"


def test_make_catalog_state_round_trips():
    c = make_catalog_state()
    assert c.tables == []
