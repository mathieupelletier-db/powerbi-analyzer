from datetime import UTC, datetime

from powerbi_analyzer.domain.catalog import (
    CatalogState,
    ClusteringInfo,
    ColumnMetadata,
    ForeignKey,
    TableMetadata,
)


def test_table_metadata_minimal():
    t = TableMetadata(
        full_name="main.gold.fact_sales",
        layer="gold",
        columns=[
            ColumnMetadata(
                name="id", data_type="bigint", is_nullable=False, max_length_observed=None
            )
        ],
        primary_key=["id"],
        foreign_keys=[],
        rely=True,
        clustering=ClusteringInfo(kind="liquid", columns=["customer_id"]),
        last_optimize_at=datetime.now(UTC),
        last_vacuum_at=None,
        predictive_optimization=True,
        has_column_stats=True,
        is_materialized_view=False,
        size_bytes=1_000_000_000,
    )
    assert t.layer == "gold"
    assert t.clustering.kind == "liquid"


def test_catalog_state_groups_tables():
    cs = CatalogState(
        tables=[],
        referenced_by_powerbi=["main.gold.fact_sales"],
    )
    assert cs.referenced_by_powerbi == ["main.gold.fact_sales"]


def test_foreign_key():
    fk = ForeignKey(
        from_columns=["customer_id"],
        to_table="main.gold.dim_customer",
        to_columns=["customer_id"],
        rely=True,
    )
    assert fk.rely is True
