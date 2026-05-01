"""WorkspaceCollector — Power BI REST + DAX INFO queries."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

import requests

from powerbi_analyzer.collectors.base import Collector, CollectorError
from powerbi_analyzer.domain.semantic_model import (
    Column,
    GatewayConfig,
    Measure,
    ParallelismConfig,
    QueryReductionConfig,
    Relationship,
    SemanticModel,
    StorageMode,
    Table,
    WorkspaceConfig,
)

# Map DAX INFO StorageMode string values to domain enum values
_STORAGE_MODE_MAP: dict[str, StorageMode] = {
    "import": StorageMode.IMPORT,
    "directquery": StorageMode.DIRECT_QUERY,
    "direct_query": StorageMode.DIRECT_QUERY,
    "dual": StorageMode.DUAL,
    "calculated": StorageMode.CALCULATED,
}

# DAX INFO cardinality codes
_CARD: dict[int, str] = {
    1: "one-to-one",
    2: "one-to-many",
    3: "many-to-one",
    4: "many-to-many",
}


class PowerBiRestClient(Protocol):
    def list_datasets(self, workspace_id: str) -> list[dict[str, Any]]: ...
    def get_workspace(self, workspace_id: str) -> dict[str, Any]: ...
    def get_capacity_settings(self, workspace_id: str) -> dict[str, Any]: ...
    def get_parallelism(self, workspace_id: str, dataset_id: str) -> dict[str, Any]: ...
    def list_gateways(self) -> list[dict[str, Any]]: ...


class XmlaRestClient(Protocol):
    def info_tables(self, workspace_id: str, dataset_id: str) -> list[dict[str, Any]]: ...
    def info_columns(self, workspace_id: str, dataset_id: str) -> list[dict[str, Any]]: ...
    def info_relationships(self, workspace_id: str, dataset_id: str) -> list[dict[str, Any]]: ...
    def info_measures(self, workspace_id: str, dataset_id: str) -> list[dict[str, Any]]: ...


class HttpPowerBiRestClient:
    BASE = "https://api.powerbi.com/v1.0/myorg"

    def __init__(self, token: str) -> None:
        self._h = {"Authorization": f"Bearer {token}"}

    def _get(self, path: str) -> Any:
        r = requests.get(self.BASE + path, headers=self._h, timeout=30)
        r.raise_for_status()
        return r.json()

    def list_datasets(self, workspace_id: str) -> list[dict[str, Any]]:
        return self._get(f"/groups/{workspace_id}/datasets")["value"]  # type: ignore[no-any-return]

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        return self._get(f"/groups/{workspace_id}")  # type: ignore[no-any-return]

    def get_capacity_settings(self, workspace_id: str) -> dict[str, Any]:
        # Placeholder; tenant-level call replaces in a follow-up
        return self._get(f"/groups/{workspace_id}/users")  # type: ignore[no-any-return]

    def get_parallelism(self, workspace_id: str, dataset_id: str) -> dict[str, Any]:
        return self._get(  # type: ignore[no-any-return]
            f"/groups/{workspace_id}/datasets/{dataset_id}/refreshParallelization"
        )

    def list_gateways(self) -> list[dict[str, Any]]:
        return self._get("/gateways")["value"]  # type: ignore[no-any-return]


class HttpXmlaRestClient:
    """Uses Execute Queries REST endpoint to run DAX INFO.* introspection."""

    BASE = "https://api.powerbi.com/v1.0/myorg"

    def __init__(self, token: str) -> None:
        self._h = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _evaluate(self, ws: str, ds: str, query: str) -> list[dict[str, Any]]:
        body = {
            "queries": [{"query": query}],
            "serializerSettings": {"includeNulls": True},
        }
        r = requests.post(
            f"{self.BASE}/groups/{ws}/datasets/{ds}/executeQueries",
            headers=self._h,
            json=body,
            timeout=60,
        )
        r.raise_for_status()
        rows: list[dict[str, Any]] = r.json()["results"][0]["tables"][0]["rows"]
        return rows

    def info_tables(self, ws: str, ds: str) -> list[dict[str, Any]]:
        return self._evaluate(ws, ds, "EVALUATE INFO.TABLES()")

    def info_columns(self, ws: str, ds: str) -> list[dict[str, Any]]:
        return self._evaluate(ws, ds, "EVALUATE INFO.COLUMNS()")

    def info_relationships(self, ws: str, ds: str) -> list[dict[str, Any]]:
        return self._evaluate(ws, ds, "EVALUATE INFO.RELATIONSHIPS()")

    def info_measures(self, ws: str, ds: str) -> list[dict[str, Any]]:
        return self._evaluate(ws, ds, "EVALUATE INFO.MEASURES()")


class WorkspaceCollector(Collector):
    mode = "workspace"

    def __init__(
        self,
        *,
        workspace_id: str,
        dataset_ids: list[str] | None,
        rest: PowerBiRestClient,
        xmla: XmlaRestClient,
    ) -> None:
        self.workspace_id = workspace_id
        self.dataset_ids = dataset_ids
        self.rest = rest
        self.xmla = xmla

    def collect(self) -> tuple[SemanticModel, WorkspaceConfig]:
        try:
            ws = self.rest.get_workspace(self.workspace_id)
            cap = self.rest.get_capacity_settings(self.workspace_id)
            datasets = self.rest.list_datasets(self.workspace_id)
        except Exception as exc:
            raise CollectorError(f"workspace REST failed: {exc}", mode=self.mode) from exc

        target_ds = self.dataset_ids or [d["id"] for d in datasets]
        if not target_ds:
            raise CollectorError("no datasets to inspect", mode=self.mode)

        # First dataset for v1 — extending to multiple is a follow-up
        ds_id = target_ds[0]
        sm = self._semantic_model(ds_id, datasets)

        gateways = self.rest.list_gateways()
        gateway: GatewayConfig | None = None
        if gateways:
            g = gateways[0]
            gateway = GatewayConfig(
                name=g.get("name", "gw"),
                cluster_size=g.get("numberOfMachines", 1),
                nodes=[],
            )

        para_payload = self.rest.get_parallelism(self.workspace_id, ds_id) or {}
        parallel = ParallelismConfig(
            max_connections_per_data_source=para_payload.get("maxConnectionsPerDataSource"),
            max_simultaneous_evaluations=para_payload.get("maxSimultaneousEvaluations"),
            max_concurrent_jobs=para_payload.get("maxConcurrentJobs"),
            max_parallelism_per_query=para_payload.get("maxParallelismPerQuery"),
        )
        cfg = WorkspaceConfig(
            workspace_id=self.workspace_id,
            capacity_region=ws.get("capacityRegion"),
            sso_enabled=bool(cap.get("sso")),
            gateway=gateway,
            parallelism=parallel,
            publish_to_pbi_service=bool(cap.get("publishToService")),
            automatic_publishing=bool(cap.get("automaticPublishing")),
        )
        return sm, cfg

    def _semantic_model(self, ds_id: str, datasets: list[dict[str, Any]]) -> SemanticModel:
        ws, ds = self.workspace_id, ds_id
        info_tables = self.xmla.info_tables(ws, ds)
        info_cols = self.xmla.info_columns(ws, ds)
        info_rels = self.xmla.info_relationships(ws, ds)
        info_meas = self.xmla.info_measures(ws, ds)

        cols_by_table: dict[str, list[Column]] = {}
        for c in info_cols:
            cols_by_table.setdefault(c["Table"], []).append(
                Column(
                    name=c["Name"],
                    data_type=str(c.get("DataType", "string")).lower(),
                    cardinality=c.get("Cardinality"),
                    is_nullable=bool(c.get("IsNullable", True)),
                    is_key=bool(c.get("IsKey", False)),
                    is_hidden=bool(c.get("IsHidden", False)),
                    summarize_by=c.get("SummarizeBy"),
                    encoding_hint=c.get("EncodingHint"),
                    max_length=c.get("MaxLength"),
                )
            )

        tables = [
            Table(
                name=t["Name"],
                columns=cols_by_table.get(t["Name"], []),
                row_count=t.get("RowCount"),
                is_hidden=bool(t.get("IsHidden", False)),
                storage_mode=_STORAGE_MODE_MAP.get(
                    str(t.get("StorageMode", "import")).lower(),
                    StorageMode.IMPORT,
                ),
                partitions=[],
                is_aggregation_table=False,
                aggregation_targets=[],
            )
            for t in info_tables
        ]

        relationships = [
            Relationship(
                from_table=r["FromTable"],
                from_column=r["FromColumn"],
                to_table=r["ToTable"],
                to_column=r["ToColumn"],
                cardinality=_CARD.get(r.get("Cardinality", 2), "one-to-many"),
                cross_filter="single" if r.get("CrossFilteringBehavior") == 1 else "both",
                is_active=bool(r.get("IsActive", True)),
                assume_referential_integrity=bool(r.get("RelyOnReferentialIntegrity", False)),
            )
            for r in info_rels
        ]

        measures = [
            Measure(
                name=m["Name"],
                table=m.get("TableName", ""),
                expression=m.get("Expression", ""),
                format_string=m.get("FormatString"),
                referenced_columns=[],
                referenced_measures=[],
            )
            for m in info_meas
        ]

        ds_meta = next((d for d in datasets if d["id"] == ds_id), {})
        return SemanticModel(
            name=ds_meta.get("name", ds_id),
            source="workspace",
            tables=tables,
            relationships=relationships,
            measures=measures,
            calculated_columns=[],
            calculated_tables=[],
            visuals_by_page={},
            aggregations=[],
            is_composite=len({t.storage_mode for t in tables}) > 1 if tables else False,
            has_hybrid_tables=False,
            parameters=[],
            query_reduction_settings=QueryReductionConfig(),
            collected_at=datetime.now(UTC),
        )
