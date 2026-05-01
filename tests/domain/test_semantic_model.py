from powerbi_analyzer.domain.semantic_model import (
    Column,
    Measure,
    Relationship,
    SemanticModel,
    StorageMode,
    Table,
)


def test_minimal_model_constructs():
    model = SemanticModel(
        name="Sales",
        source="pbix",
        tables=[],
        relationships=[],
        measures=[],
        calculated_columns=[],
        calculated_tables=[],
        visuals_by_page={},
        aggregations=[],
        is_composite=False,
        has_hybrid_tables=False,
        parameters=[],
        query_reduction_settings=None,
    )
    assert model.name == "Sales"
    assert model.source == "pbix"


def test_full_model_round_trips_json():
    table = Table(
        name="Fact_Sales",
        columns=[
            Column(
                name="OrderId",
                data_type="int64",
                is_nullable=False,
                is_key=True,
                is_hidden=False,
                cardinality=1_000_000,
            )
        ],
        row_count=1_000_000,
        is_hidden=False,
        storage_mode=StorageMode.DIRECT_QUERY,
        partitions=[],
        is_aggregation_table=False,
        aggregation_targets=[],
    )
    rel = Relationship(
        from_table="Fact_Sales",
        from_column="CustomerId",
        to_table="Dim_Customer",
        to_column="CustomerId",
        cardinality="many-to-one",
        cross_filter="single",
        is_active=True,
        assume_referential_integrity=False,
    )
    measure = Measure(
        name="TotalRevenue",
        table="Fact_Sales",
        expression="SUM(Fact_Sales[Revenue])",
        format_string="$#,##0",
        referenced_columns=["Fact_Sales[Revenue]"],
        referenced_measures=[],
    )
    model = SemanticModel(
        name="Sales",
        source="workspace",
        tables=[table],
        relationships=[rel],
        measures=[measure],
        calculated_columns=[],
        calculated_tables=[],
        visuals_by_page={},
        aggregations=[],
        is_composite=False,
        has_hybrid_tables=False,
        parameters=[],
        query_reduction_settings=None,
    )
    payload = model.model_dump_json()
    restored = SemanticModel.model_validate_json(payload)
    assert restored.tables[0].columns[0].is_key is True
    assert restored.relationships[0].cardinality == "many-to-one"
