"""Catalog + table-metadata domain types — produced by DatabricksCollector."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_FROZEN = ConfigDict(frozen=True)


class ColumnMetadata(BaseModel):
    model_config = _FROZEN
    name: str
    data_type: str
    is_nullable: bool
    max_length_observed: int | None = None


class ForeignKey(BaseModel):
    model_config = _FROZEN
    from_columns: list[str]
    to_table: str
    to_columns: list[str]
    rely: bool | None = None


class ClusteringInfo(BaseModel):
    model_config = _FROZEN
    kind: Literal["liquid", "zorder", "partitioned", "none"]
    columns: list[str] = Field(default_factory=list)


class TableMetadata(BaseModel):
    model_config = _FROZEN
    full_name: str
    layer: Literal["bronze", "silver", "gold", "unknown"]
    columns: list[ColumnMetadata]
    primary_key: list[str] | None = None
    foreign_keys: list[ForeignKey] = Field(default_factory=list)
    # None = unknown (Tables API unavailable); information_schema does not expose RELY.
    rely: bool | None = None
    clustering: ClusteringInfo
    last_optimize_at: datetime | None = None
    last_vacuum_at: datetime | None = None
    predictive_optimization: bool = False
    # None = not collected.
    has_column_stats: bool | None = None
    is_materialized_view: bool = False
    size_bytes: int | None = None


class CatalogState(BaseModel):
    model_config = _FROZEN
    tables: list[TableMetadata] = Field(default_factory=list)
    referenced_by_powerbi: list[str] = Field(default_factory=list)
