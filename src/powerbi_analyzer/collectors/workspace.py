"""WorkspaceCollector — Power BI REST + DAX INFO queries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar, Protocol

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


def _raise_with_body(r: requests.Response, context: str) -> None:
    """Re-raise an HTTP error with the Power BI error body attached.

    Power BI returns a JSON body like {"error": {"code": "...", "message": "..."}}
    on most failures; raise_for_status alone hides it.
    """
    if r.ok:
        return
    detail = ""
    try:
        body = r.json()
        err = body.get("error", body) if isinstance(body, dict) else body
        if isinstance(err, dict):
            code = err.get("code") or err.get("errorCode") or ""
            msg = err.get("message") or err.get("pbi.error", {}).get("code", "")
            detail = f" — {code}: {msg}".rstrip(": ").rstrip(" —")
        else:
            detail = f" — {body}"
    except ValueError:
        if r.text:
            detail = f" — {r.text[:500]}"
    raise requests.HTTPError(f"{r.status_code} {r.reason} for {context}{detail}", response=r)


class HttpPowerBiRestClient:
    BASE = "https://api.powerbi.com/v1.0/myorg"

    def __init__(self, token: str) -> None:
        self._h = {"Authorization": f"Bearer {token}"}

    def _get(self, path: str) -> Any:
        r = requests.get(self.BASE + path, headers=self._h, timeout=30)
        _raise_with_body(r, f"GET {path}")
        return r.json()

    def _get_optional(self, path: str) -> dict[str, Any]:
        """Like _get, but returns {} for 404/403 (endpoint unsupported on this resource).

        Several Power BI endpoints (refreshParallelization, gateway listing) are
        unsupported on Fabric default semantic models or restricted by tenant
        policy. They're optional config metadata, so degrade gracefully.
        """
        r = requests.get(self.BASE + path, headers=self._h, timeout=30)
        if r.status_code in (403, 404):
            return {}
        _raise_with_body(r, f"GET {path}")
        body = r.json()
        return body if isinstance(body, dict) else {}

    def list_datasets(self, workspace_id: str) -> list[dict[str, Any]]:
        return self._get(f"/groups/{workspace_id}/datasets")["value"]  # type: ignore[no-any-return]

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        return self._get(f"/groups/{workspace_id}")  # type: ignore[no-any-return]

    def get_capacity_settings(self, workspace_id: str) -> dict[str, Any]:
        # Placeholder; tenant-level call replaces in a follow-up
        return self._get_optional(f"/groups/{workspace_id}/users")

    def get_parallelism(self, workspace_id: str, dataset_id: str) -> dict[str, Any]:
        return self._get_optional(
            f"/groups/{workspace_id}/datasets/{dataset_id}/refreshParallelization"
        )

    def list_gateways(self) -> list[dict[str, Any]]:
        r = requests.get(self.BASE + "/gateways", headers=self._h, timeout=30)
        if r.status_code in (401, 403, 404):
            return []
        _raise_with_body(r, "GET /gateways")
        return r.json().get("value", []) or []  # type: ignore[no-any-return]


class HttpXmlaRestClient:
    """Uses Execute Queries REST endpoint to run DAX INFO.* introspection.

    Fabric default semantic models (auto-generated over Lakehouses/Warehouses)
    reject classic INFO.* with DatasetExecuteQueriesError but accept the modern
    INFO.VIEW.* aliases. We try classic first and fall back transparently.
    """

    BASE = "https://api.powerbi.com/v1.0/myorg"

    # INFO.VIEW.RELATIONSHIPS encodes cardinality as two strings; classic
    # INFO.RELATIONSHIPS uses a single integer code. Bridge the two.
    _CARD_PAIR_TO_CODE: ClassVar[dict[tuple[str, str], int]] = {
        ("One", "One"): 1,
        ("One", "Many"): 2,
        ("Many", "One"): 3,
        ("Many", "Many"): 4,
    }
    _CROSS_FILTER_TO_CODE: ClassVar[dict[str, int]] = {
        "OneDirection": 1,
        "BothDirections": 2,
    }

    def __init__(self, token: str) -> None:
        self._h = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _strip_keys(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # executeQueries returns each column name wrapped in brackets, e.g.
        # "[Name]". Unwrap so callers can read fields by their plain name.
        return [{k.strip("[]"): v for k, v in row.items()} for row in rows]

    def _evaluate_raw(self, ws: str, ds: str, query: str) -> list[dict[str, Any]]:
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
        _raise_with_body(r, f"POST executeQueries (workspace {ws}, dataset {ds}, query {query!r})")
        rows: list[dict[str, Any]] = r.json()["results"][0]["tables"][0]["rows"]
        return self._strip_keys(rows)

    def _evaluate_with_view_fallback(
        self, ws: str, ds: str, classic: str, view: str
    ) -> tuple[list[dict[str, Any]], bool]:
        """Try the classic INFO query; on DatasetExecuteQueriesError, retry with VIEW."""
        try:
            return self._evaluate_raw(ws, ds, classic), False
        except requests.HTTPError as exc:
            if "DatasetExecuteQueriesError" in str(exc):
                return self._evaluate_raw(ws, ds, view), True
            raise

    def info_tables(self, ws: str, ds: str) -> list[dict[str, Any]]:
        rows, _ = self._evaluate_with_view_fallback(
            ws, ds, "EVALUATE INFO.TABLES()", "EVALUATE INFO.VIEW.TABLES()"
        )
        return rows

    def info_columns(self, ws: str, ds: str) -> list[dict[str, Any]]:
        rows, _ = self._evaluate_with_view_fallback(
            ws, ds, "EVALUATE INFO.COLUMNS()", "EVALUATE INFO.VIEW.COLUMNS()"
        )
        return rows

    def info_relationships(self, ws: str, ds: str) -> list[dict[str, Any]]:
        rows, used_view = self._evaluate_with_view_fallback(
            ws,
            ds,
            "EVALUATE INFO.RELATIONSHIPS()",
            "EVALUATE INFO.VIEW.RELATIONSHIPS()",
        )
        if used_view:
            for r in rows:
                if "Cardinality" not in r:
                    pair = (r.get("FromCardinality"), r.get("ToCardinality"))
                    r["Cardinality"] = self._CARD_PAIR_TO_CODE.get(pair, 3)
                xf = r.get("CrossFilteringBehavior")
                if isinstance(xf, str):
                    r["CrossFilteringBehavior"] = self._CROSS_FILTER_TO_CODE.get(xf, 1)
        return rows

    def info_measures(self, ws: str, ds: str) -> list[dict[str, Any]]:
        rows, used_view = self._evaluate_with_view_fallback(
            ws, ds, "EVALUATE INFO.MEASURES()", "EVALUATE INFO.VIEW.MEASURES()"
        )
        if used_view:
            for r in rows:
                if "TableName" not in r and "Table" in r:
                    r["TableName"] = r["Table"]
        return rows


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
            tname = c.get("Table")
            cname = c.get("Name")
            if not tname or not cname:
                continue
            cols_by_table.setdefault(tname, []).append(
                Column(
                    name=cname,
                    data_type=str(c.get("DataType") or "string").lower(),
                    cardinality=c.get("Cardinality"),
                    is_nullable=bool(c.get("IsNullable", True)),
                    is_key=bool(c.get("IsKey", False)),
                    is_hidden=bool(c.get("IsHidden", False)),
                    summarize_by=c.get("SummarizeBy"),
                    encoding_hint=c.get("EncodingHint"),
                    max_length=c.get("MaxLength"),
                )
            )

        tables: list[Table] = []
        for t in info_tables:
            tname = t.get("Name")
            if not tname:
                continue
            tables.append(
                Table(
                    name=tname,
                    columns=cols_by_table.get(tname, []),
                    row_count=t.get("RowCount"),
                    is_hidden=bool(t.get("IsHidden", False)),
                    storage_mode=_STORAGE_MODE_MAP.get(
                        str(t.get("StorageMode") or "import").lower(),
                        StorageMode.IMPORT,
                    ),
                    partitions=[],
                    is_aggregation_table=False,
                    aggregation_targets=[],
                )
            )

        relationships: list[Relationship] = []
        for r in info_rels:
            ft, fc = r.get("FromTable"), r.get("FromColumn")
            tt, tc = r.get("ToTable"), r.get("ToColumn")
            if not (ft and fc and tt and tc):
                continue
            relationships.append(
                Relationship(
                    from_table=ft,
                    from_column=fc,
                    to_table=tt,
                    to_column=tc,
                    cardinality=_CARD.get(r.get("Cardinality") or 2, "one-to-many"),
                    cross_filter="single" if r.get("CrossFilteringBehavior") == 1 else "both",
                    is_active=bool(r.get("IsActive", True)),
                    assume_referential_integrity=bool(r.get("RelyOnReferentialIntegrity", False)),
                )
            )

        measures: list[Measure] = []
        for m in info_meas:
            name = m.get("Name")
            if not name:
                continue
            measures.append(
                Measure(
                    name=name,
                    table=m.get("TableName") or "",
                    expression=m.get("Expression") or "",
                    format_string=m.get("FormatString"),
                    referenced_columns=[],
                    referenced_measures=[],
                )
            )

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
