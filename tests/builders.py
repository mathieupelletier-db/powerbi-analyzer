"""Shared Pydantic builders for unit tests. Keep test code compact."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from powerbi_analyzer.domain.catalog import (
    CatalogState,
    ClusteringInfo,
    ColumnMetadata,
    ForeignKey,
    TableMetadata,
)
from powerbi_analyzer.domain.semantic_model import (
    Column,
    Measure,
    ParallelismConfig,
    Relationship,
    SemanticModel,
    StorageMode,
    Table,
    WorkspaceConfig,
)
from powerbi_analyzer.domain.warehouse import (
    QueryHistoryEntry,
    WarehouseEvent,
    WarehouseState,
)


def make_column(**overrides: Any) -> Column:
    base: dict[str, Any] = dict(
        name="col",
        data_type="int64",
        cardinality=None,
        is_nullable=True,
        is_key=False,
        is_hidden=False,
        summarize_by=None,
        encoding_hint=None,
        max_length=None,
    )
    base.update(overrides)
    return Column(**base)


def make_table(**overrides: Any) -> Table:
    base: dict[str, Any] = dict(
        name="T",
        columns=[],
        row_count=None,
        is_hidden=False,
        storage_mode=StorageMode.IMPORT,
        partitions=[],
        is_aggregation_table=False,
        aggregation_targets=[],
    )
    base.update(overrides)
    return Table(**base)


def make_relationship(**overrides: Any) -> Relationship:
    base: dict[str, Any] = dict(
        from_table="A",
        from_column="id",
        to_table="B",
        to_column="a_id",
        cardinality="one-to-many",
        cross_filter="single",
        is_active=True,
        assume_referential_integrity=False,
    )
    base.update(overrides)
    return Relationship(**base)


def make_measure(**overrides: Any) -> Measure:
    base: dict[str, Any] = dict(
        name="M",
        table="T",
        expression="0",
        format_string=None,
        referenced_columns=[],
        referenced_measures=[],
    )
    base.update(overrides)
    return Measure(**base)


def make_semantic_model(**overrides: Any) -> SemanticModel:
    base: dict[str, Any] = dict(
        name="model",
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
        collected_at=datetime.now(UTC),
    )
    base.update(overrides)
    return SemanticModel(**base)


def make_workspace_config(**overrides: Any) -> WorkspaceConfig:
    base: dict[str, Any] = dict(
        workspace_id="ws",
        capacity_region="eastus",
        sso_enabled=True,
        gateway=None,
        parallelism=ParallelismConfig(),
        publish_to_pbi_service=False,
        automatic_publishing=False,
    )
    base.update(overrides)
    return WorkspaceConfig(**base)


def make_query(**overrides: Any) -> QueryHistoryEntry:
    now = datetime.now(UTC)
    base: dict[str, Any] = dict(
        query_id="q",
        warehouse_id="wh",
        all_purpose_cluster_id=None,
        client_application="Power BI Desktop",
        statement_type="SELECT",
        started_at=now,
        ended_at=now,
        execution_time_ms=100,
        queue_duration_ms=0,
        compute_used_mb=64,
        rows_produced=10,
        spilled_to_disk=False,
        referenced_tables=[],
    )
    base.update(overrides)
    return QueryHistoryEntry(**base)


def make_warehouse(**overrides: Any) -> WarehouseState:
    base: dict[str, Any] = dict(
        warehouse_id="wh",
        name="bi",
        type="serverless",
        cluster_size="Medium",
        auto_stop_mins=10,
        min_clusters=1,
        max_clusters=4,
        region="us-east-1",
        query_history=[],
        events=[],
    )
    base.update(overrides)
    return WarehouseState(**base)


def make_warehouse_event(**overrides: Any) -> WarehouseEvent:
    base: dict[str, Any] = dict(
        event_time=datetime.now(UTC),
        warehouse_id="wh",
        event_type="SCALED_UP",
        cluster_count=2,
    )
    base.update(overrides)
    return WarehouseEvent(**base)


def make_table_metadata(**overrides: Any) -> TableMetadata:
    base: dict[str, Any] = dict(
        full_name="main.gold.t",
        layer="gold",
        columns=[
            ColumnMetadata(
                name="id", data_type="bigint", is_nullable=False, max_length_observed=None
            )
        ],
        primary_key=["id"],
        foreign_keys=[],
        rely=True,
        clustering=ClusteringInfo(kind="liquid", columns=["id"]),
        last_optimize_at=datetime.now(UTC),
        last_vacuum_at=datetime.now(UTC),
        predictive_optimization=True,
        has_column_stats=True,
        is_materialized_view=False,
        size_bytes=1_000_000,
    )
    base.update(overrides)
    return TableMetadata(**base)


def make_foreign_key(**overrides: Any) -> ForeignKey:
    base: dict[str, Any] = dict(
        from_columns=["fk"],
        to_table="main.gold.dim",
        to_columns=["pk"],
        rely=True,
    )
    base.update(overrides)
    return ForeignKey(**base)


def make_catalog_state(**overrides: Any) -> CatalogState:
    base: dict[str, Any] = dict(tables=[], referenced_by_powerbi=[])
    base.update(overrides)
    return CatalogState(**base)
