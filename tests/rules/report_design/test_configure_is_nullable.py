from powerbi_analyzer.domain.catalog import ColumnMetadata
from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.report_design import configure_is_nullable as rule

from tests.builders import (
    make_catalog_state,
    make_column,
    make_semantic_model,
    make_table,
    make_table_metadata,
)


def test_passes_when_aligned():
    m = make_semantic_model(
        tables=[make_table(name="t", columns=[make_column(name="id", is_nullable=False)])]
    )
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.t",
                columns=[
                    ColumnMetadata(
                        name="id", data_type="bigint", is_nullable=False, max_length_observed=None
                    )
                ],
            )
        ]
    )
    assert rule.check(m, cat).status is Status.PASS


def test_fails_when_model_says_nullable_but_source_not_null():
    m = make_semantic_model(
        tables=[make_table(name="t", columns=[make_column(name="id", is_nullable=True)])]
    )
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.t",
                columns=[
                    ColumnMetadata(
                        name="id", data_type="bigint", is_nullable=False, max_length_observed=None
                    )
                ],
            )
        ]
    )
    f = rule.check(m, cat)
    assert f.status is Status.FAIL
    assert "t[id]" in f.evidence["columns"]
