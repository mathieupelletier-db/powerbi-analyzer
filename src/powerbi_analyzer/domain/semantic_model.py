"""Semantic-model domain types — produced by both PbixCollector and WorkspaceCollector."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StorageMode(StrEnum):
    IMPORT = "import"
    DIRECT_QUERY = "direct_query"
    DUAL = "dual"
    CALCULATED = "calculated"


_FROZEN = ConfigDict(frozen=True, str_strip_whitespace=True)


class Column(BaseModel):
    model_config = _FROZEN
    name: str
    data_type: str
    cardinality: int | None = None
    is_nullable: bool = True
    is_key: bool = False
    is_hidden: bool = False
    summarize_by: str | None = None
    encoding_hint: Literal["value", "hash", None] = None
    max_length: int | None = None  # used by DP-005


class RefreshPolicy(BaseModel):
    model_config = _FROZEN
    rolling_window_unit: Literal["day", "month", "quarter", "year"]
    rolling_window_size: int
    incremental_unit: Literal["day", "month", "quarter", "year"]
    incremental_size: int
    real_time: bool = False  # hybrid-table flag


class Partition(BaseModel):
    model_config = _FROZEN
    name: str
    source_type: Literal["m", "dax", "calculated", "calculatedTable", "entity"]
    source_expression: str | None = None
    refresh_policy: RefreshPolicy | None = None


class Table(BaseModel):
    model_config = _FROZEN
    name: str
    columns: list[Column] = Field(default_factory=list)
    row_count: int | None = None
    is_hidden: bool = False
    storage_mode: StorageMode
    partitions: list[Partition] = Field(default_factory=list)
    is_aggregation_table: bool = False
    aggregation_targets: list[str] = Field(default_factory=list)


class Relationship(BaseModel):
    model_config = _FROZEN
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: Literal["one-to-one", "one-to-many", "many-to-one", "many-to-many"]
    cross_filter: Literal["single", "both", "none"]
    is_active: bool = True
    assume_referential_integrity: bool = False


class Measure(BaseModel):
    model_config = _FROZEN
    name: str
    table: str
    expression: str
    format_string: str | None = None
    referenced_columns: list[str] = Field(default_factory=list)
    referenced_measures: list[str] = Field(default_factory=list)


class CalculatedColumn(BaseModel):
    model_config = _FROZEN
    name: str
    table: str
    expression: str
    data_type: str


class CalculatedTable(BaseModel):
    model_config = _FROZEN
    name: str
    expression: str


class Visual(BaseModel):
    model_config = _FROZEN
    page: str
    visual_type: str
    fields_used: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)


class Aggregation(BaseModel):
    model_config = _FROZEN
    base_table: str
    agg_table: str
    column_map: dict[str, str]


class Parameter(BaseModel):
    model_config = _FROZEN
    name: str
    data_type: str
    current_value: str | None = None


class QueryReductionConfig(BaseModel):
    model_config = _FROZEN
    apply_all_slicers_button: bool = False
    disable_cross_highlight: bool = False


class SemanticModel(BaseModel):
    model_config = _FROZEN
    name: str
    source: Literal["pbix", "pbip", "workspace"]
    tables: list[Table]
    relationships: list[Relationship]
    measures: list[Measure]
    calculated_columns: list[CalculatedColumn]
    calculated_tables: list[CalculatedTable]
    visuals_by_page: dict[str, list[Visual]]
    aggregations: list[Aggregation]
    is_composite: bool
    has_hybrid_tables: bool
    parameters: list[Parameter]
    query_reduction_settings: QueryReductionConfig | None
    collected_at: datetime | None = None


class GatewayConfig(BaseModel):
    model_config = _FROZEN
    name: str
    cluster_size: int
    nodes: list[str] = Field(default_factory=list)


class ParallelismConfig(BaseModel):
    model_config = _FROZEN
    max_connections_per_data_source: int | None = None
    max_simultaneous_evaluations: int | None = None
    max_concurrent_jobs: int | None = None
    max_parallelism_per_query: int | None = None


class WorkspaceConfig(BaseModel):
    model_config = _FROZEN
    workspace_id: str
    capacity_region: str | None = None
    sso_enabled: bool = False
    gateway: GatewayConfig | None = None
    parallelism: ParallelismConfig = Field(default_factory=ParallelismConfig)
    publish_to_pbi_service: bool = False
    automatic_publishing: bool = False
