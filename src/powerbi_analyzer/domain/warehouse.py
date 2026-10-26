"""Warehouse + query-history domain types — produced by DatabricksCollector."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_FROZEN = ConfigDict(frozen=True)

_NON_ALPHA = re.compile(r"[^a-z]")


def is_powerbi_client(client_application: str | None) -> bool:
    """True if a query-history client_application string identifies Power BI.

    The value is client-reported and not standardized ("Power BI", "PowerBI",
    "Power BI Desktop", ...), so compare on letters only, case-insensitively.
    Keep in sync with collectors.databricks.POWERBI_CLIENT_SQL.
    """
    return "powerbi" in _NON_ALPHA.sub("", (client_application or "").lower())


class QueryHistoryEntry(BaseModel):
    model_config = _FROZEN
    query_id: str
    warehouse_id: str | None
    all_purpose_cluster_id: str | None
    client_application: str | None
    statement_type: str
    started_at: datetime
    ended_at: datetime | None
    execution_time_ms: int
    queue_duration_ms: int
    compute_used_mb: int | None = None
    rows_produced: int | None = None
    spilled_to_disk: bool = False
    referenced_tables: list[str] = Field(default_factory=list)


class WarehouseEvent(BaseModel):
    model_config = _FROZEN
    event_time: datetime
    warehouse_id: str
    event_type: str
    cluster_count: int | None = None


class WarehouseState(BaseModel):
    model_config = _FROZEN
    warehouse_id: str
    name: str
    type: Literal["serverless", "pro", "classic"]
    cluster_size: str
    auto_stop_mins: int | None
    min_clusters: int
    max_clusters: int
    region: str
    query_history: list[QueryHistoryEntry] = Field(default_factory=list)
    events: list[WarehouseEvent] = Field(default_factory=list)
    # Set when system.access.table_lineage could not be read; referenced_tables is then empty.
    table_lineage_error: str | None = None
