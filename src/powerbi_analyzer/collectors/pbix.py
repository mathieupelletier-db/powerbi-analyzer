"""PbixCollector — parse .pbix and .pbip into SemanticModel via pbixray and JSON."""

from __future__ import annotations

import contextlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd
from pbixray import PBIXRay  # type: ignore[import-untyped]

from powerbi_analyzer.collectors.base import Collector, CollectorError
from powerbi_analyzer.domain.semantic_model import (
    CalculatedColumn,
    CalculatedTable,
    Column,
    Measure,
    Partition,
    QueryReductionConfig,
    Relationship,
    SemanticModel,
    StorageMode,
    Table,
    Visual,
)

_CARDINALITY: dict[str, str] = {
    # pbixray DataFrame values
    "1:1": "one-to-one",
    "1:M": "one-to-many",
    "M:1": "many-to-one",
    "M:M": "many-to-many",
    # Long-form values (defensive — older pbixray or other sources)
    "OneToOne": "one-to-one",
    "OneToMany": "one-to-many",
    "ManyToOne": "many-to-one",
    "ManyToMany": "many-to-many",
}
_CROSS_FILTER: dict[str, str] = {
    "Single": "single",
    "Both": "both",
    "None": "none",
    "OneDirection": "single",
    "BothDirections": "both",
}
# model.bim JSON cardinality values (already lower-kebab or hyphenated)
_BIM_CARDINALITY: dict[str, str] = {
    "one-to-one": "one-to-one",
    "one-to-many": "one-to-many",
    "many-to-one": "many-to-one",
    "many-to-many": "many-to-many",
}
_BIM_CROSS_FILTER: dict[str, str] = {
    "single": "single",
    "both": "both",
    "none": "none",
}
_BIM_STORAGE_MODE: dict[str, StorageMode] = {
    "import": StorageMode.IMPORT,
    "directquery": StorageMode.DIRECT_QUERY,
    "direct_query": StorageMode.DIRECT_QUERY,
    "dual": StorageMode.DUAL,
    "calculated": StorageMode.CALCULATED,
}

# Shared Literal type aliases used in casts throughout this module
_CardinalityType = Literal["one-to-one", "one-to-many", "many-to-one", "many-to-many"]
_CrossFilterType = Literal["single", "both", "none"]
_SourceType = Literal["m", "dax", "calculated", "calculatedTable", "entity"]


def _records(obj: Any) -> list[dict[str, Any]]:
    """Normalize a pbixray attribute into a list of plain dicts.

    pbixray 0.5 returns pandas DataFrames; older releases or test mocks may
    pass list-of-dicts or empty containers.
    """
    if obj is None:
        return []
    if isinstance(obj, pd.DataFrame):
        if obj.empty:
            return []
        return cast(list[dict[str, Any]], obj.to_dict(orient="records"))
    if isinstance(obj, list):
        return [r for r in obj if isinstance(r, dict)]
    return []


class PbixCollector(Collector):
    mode = "pbix"

    def __init__(self, *, path: Path) -> None:
        self.path = Path(path)

    def collect(self) -> SemanticModel:
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        if self.path.is_dir() or self.path.suffix == ".pbip":
            return self._collect_pbip(self.path)
        try:
            return self._collect_pbix(self.path)
        except CollectorError:
            raise
        except Exception as exc:
            raise CollectorError(f"failed to parse {self.path}: {exc}", mode=self.mode) from exc

    # ------------------------------------------------------------------
    # .pbix via pbixray
    # ------------------------------------------------------------------

    def _collect_pbix(self, path: Path) -> SemanticModel:
        ray = PBIXRay(str(path))

        # pbixray 0.5 exposes most attributes as pandas DataFrames; older or
        # mocked variants may return list-of-dicts. Normalize both.
        schema_records = _records(ray.schema)
        stats_records = _records(ray.statistics)

        # Per-column distinct count (pbixray "Cardinality" on statistics)
        cardinality_by_col: dict[tuple[str, str], int] = {}
        for s in stats_records:
            tn, cn, card = s.get("TableName"), s.get("ColumnName"), s.get("Cardinality")
            if tn and cn and card is not None:
                with contextlib.suppress(TypeError, ValueError):
                    cardinality_by_col[(tn, cn)] = int(card)

        # Group schema rows by table for O(1) lookup
        schema_by_table: dict[str, list[dict[str, Any]]] = {}
        for row in schema_records:
            schema_by_table.setdefault(row.get("TableName", ""), []).append(row)

        tables: list[Table] = []
        for tname in ray.tables:
            cols: list[Column] = []
            for col in schema_by_table.get(tname, []):
                col_name = col.get("ColumnName")
                if not col_name:
                    continue
                cols.append(
                    Column(
                        name=col_name,
                        data_type=str(col.get("PandasDataType") or col.get("DataType") or "string"),
                        cardinality=cardinality_by_col.get((tname, col_name)),
                        is_nullable=bool(col.get("IsNullable", True)),
                        is_key=bool(col.get("IsKey", False)),
                        is_hidden=bool(col.get("IsHidden", False)),
                        summarize_by=col.get("SummarizeBy"),
                        encoding_hint=col.get("EncodingHint"),
                        max_length=col.get("MaxLength"),
                    )
                )
            tables.append(
                Table(
                    name=tname,
                    columns=cols,
                    row_count=None,
                    is_hidden=False,
                    storage_mode=StorageMode.IMPORT,
                    partitions=[],
                    is_aggregation_table=False,
                    aggregation_targets=[],
                )
            )

        relationships: list[Relationship] = []
        for r in _records(ray.relationships):
            from_table = r.get("FromTableName") or r.get("FromTable")
            to_table = r.get("ToTableName") or r.get("ToTable")
            from_col = r.get("FromColumnName") or r.get("FromColumn")
            to_col = r.get("ToColumnName") or r.get("ToColumn")
            if not (from_table and to_table and from_col and to_col):
                # Skip auto-DateTable artifacts that have no resolved target
                continue
            card_raw = str(r.get("Cardinality") or "M:1")
            cross_raw = str(r.get("CrossFilteringBehavior") or r.get("CrossFilter") or "Single")
            relationships.append(
                Relationship(
                    from_table=from_table,
                    from_column=from_col,
                    to_table=to_table,
                    to_column=to_col,
                    cardinality=cast(_CardinalityType, _CARDINALITY.get(card_raw, "many-to-one")),
                    cross_filter=cast(_CrossFilterType, _CROSS_FILTER.get(cross_raw, "single")),
                    is_active=bool(r.get("IsActive", True)),
                    assume_referential_integrity=bool(r.get("RelyOnReferentialIntegrity", False)),
                )
            )

        measures: list[Measure] = []
        for m in _records(ray.dax_measures):
            name = m.get("Name")
            if not name:
                continue
            measures.append(
                Measure(
                    name=name,
                    table=m.get("TableName") or m.get("Table") or "",
                    expression=m.get("Expression") or "",
                    format_string=m.get("FormatString"),
                    referenced_columns=[],
                    referenced_measures=[],
                )
            )

        calculated_columns: list[CalculatedColumn] = []
        for c in _records(ray.dax_columns):
            name = c.get("ColumnName") or c.get("Name")
            if not name:
                continue
            calculated_columns.append(
                CalculatedColumn(
                    name=name,
                    table=c.get("TableName") or c.get("Table") or "",
                    expression=c.get("Expression") or "",
                    data_type=str(c.get("DataType") or "string"),
                )
            )

        calculated_tables: list[CalculatedTable] = []
        for t in _records(ray.dax_tables):
            name = t.get("TableName") or t.get("Name")
            if not name:
                continue
            calculated_tables.append(
                CalculatedTable(name=name, expression=t.get("Expression") or "")
            )

        visuals_by_page = self._extract_visuals(path)

        return SemanticModel(
            name=path.stem,
            source="pbix",
            tables=tables,
            relationships=relationships,
            measures=measures,
            calculated_columns=calculated_columns,
            calculated_tables=calculated_tables,
            visuals_by_page=visuals_by_page,
            aggregations=[],
            is_composite=(len({t.storage_mode for t in tables}) > 1 if tables else False),
            has_hybrid_tables=False,
            parameters=[],
            query_reduction_settings=QueryReductionConfig(),
            collected_at=datetime.now(UTC),
        )

    @staticmethod
    def _extract_visuals(path: Path) -> dict[str, list[Visual]]:
        visuals: dict[str, list[Visual]] = {}
        try:
            with zipfile.ZipFile(path) as zf:
                if "Report/Layout" not in zf.namelist():
                    return visuals
                raw = zf.read("Report/Layout")
                try:
                    layout_text = raw.decode("utf-16-le").lstrip("﻿")
                except UnicodeDecodeError:
                    layout_text = raw.decode("utf-8", errors="replace")
                layout: dict[str, Any] = json.loads(layout_text)
                for section in layout.get("sections", []):
                    page_name: str = section.get("displayName", section.get("name", "Page"))
                    page_visuals: list[Visual] = []
                    for vc in section.get("visualContainers", []):
                        cfg_raw = vc.get("config", "{}")
                        try:
                            cfg: dict[str, Any] = (
                                json.loads(cfg_raw) if isinstance(cfg_raw, str) else cfg_raw
                            )
                        except json.JSONDecodeError:
                            cfg = {}
                        vtype = cfg.get("singleVisual", {}).get("visualType", "unknown")
                        page_visuals.append(
                            Visual(page=page_name, visual_type=vtype, fields_used=[], filters=[])
                        )
                    visuals[page_name] = page_visuals
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError):
            pass
        return visuals

    # ------------------------------------------------------------------
    # .pbip via model.bim JSON
    # ------------------------------------------------------------------

    def _collect_pbip(self, path: Path) -> SemanticModel:
        bim_files = list(path.rglob("model.bim"))
        if not bim_files:
            raise CollectorError(f"No model.bim found under {path}", mode=self.mode)
        bim_path = bim_files[0]
        bim: dict[str, Any] = json.loads(bim_path.read_text(encoding="utf-8"))
        name = bim.get("name", path.stem)
        model = bim.get("model", {})
        return _semantic_model_from_bim(name=name, model=model)


# ------------------------------------------------------------------
# BIM parser helpers
# ------------------------------------------------------------------


def _semantic_model_from_bim(*, name: str, model: dict[str, Any]) -> SemanticModel:
    raw_tables: list[dict[str, Any]] = model.get("tables", [])

    tables: list[Table] = []
    measures: list[Measure] = []
    calculated_columns: list[CalculatedColumn] = []

    for t in raw_tables:
        tname: str = t["name"]

        # Columns
        cols: list[Column] = []
        for c in t.get("columns", []):
            # Calculated columns have type == "calculated"
            if c.get("type") == "calculated":
                calculated_columns.append(
                    CalculatedColumn(
                        name=c["name"],
                        table=tname,
                        expression=c.get("expression", ""),
                        data_type=c.get("dataType", "string"),
                    )
                )
                # Also add as a regular column so schema is visible
                cols.append(
                    Column(
                        name=c["name"],
                        data_type=c.get("dataType", "string"),
                        is_nullable=bool(c.get("isNullable", True)),
                        is_key=bool(c.get("isKey", False)),
                        is_hidden=bool(c.get("isHidden", False)),
                    )
                )
            else:
                cols.append(
                    Column(
                        name=c["name"],
                        data_type=c.get("dataType", "string"),
                        is_nullable=bool(c.get("isNullable", True)),
                        is_key=bool(c.get("isKey", False)),
                        is_hidden=bool(c.get("isHidden", False)),
                    )
                )

        # Partitions (for storage mode)
        raw_partitions: list[dict[str, Any]] = t.get("partitions", [])
        partitions: list[Partition] = []
        storage_mode = StorageMode.IMPORT
        for p in raw_partitions:
            mode_str = p.get("mode", "import").lower().replace(" ", "_")
            pmode = _BIM_STORAGE_MODE.get(mode_str, StorageMode.IMPORT)
            storage_mode = pmode  # last partition wins (usually only one)
            src = p.get("source", {})
            partitions.append(
                Partition(
                    name=p["name"],
                    source_type=cast(_SourceType, src.get("type", "m")),
                    source_expression=src.get("expression"),
                )
            )

        # Measures
        for m in t.get("measures", []):
            measures.append(
                Measure(
                    name=m["name"],
                    table=tname,
                    expression=m.get("expression", ""),
                    format_string=m.get("formatString"),
                    referenced_columns=[],
                    referenced_measures=[],
                )
            )

        tables.append(
            Table(
                name=tname,
                columns=cols,
                is_hidden=bool(t.get("isHidden", False)),
                storage_mode=storage_mode,
                partitions=partitions,
                is_aggregation_table=False,
                aggregation_targets=[],
            )
        )

    # Relationships
    relationships: list[Relationship] = []
    for r in model.get("relationships", []):
        card_raw = r.get("cardinality", "many-to-one").lower()
        cross_raw = r.get("crossFilteringBehavior", "single").lower()
        relationships.append(
            Relationship(
                from_table=r["fromTable"],
                from_column=r["fromColumn"],
                to_table=r["toTable"],
                to_column=r["toColumn"],
                cardinality=cast(_CardinalityType, _BIM_CARDINALITY.get(card_raw, "many-to-one")),
                cross_filter=cast(_CrossFilterType, _BIM_CROSS_FILTER.get(cross_raw, "single")),
                is_active=bool(r.get("isActive", True)),
                assume_referential_integrity=bool(r.get("relyOnReferentialIntegrity", False)),
            )
        )

    storage_modes = {t.storage_mode for t in tables}
    is_composite = len(storage_modes) > 1

    return SemanticModel(
        name=name,
        source="pbip",
        tables=tables,
        relationships=relationships,
        measures=measures,
        calculated_columns=calculated_columns,
        calculated_tables=[],
        visuals_by_page={},
        aggregations=[],
        is_composite=is_composite,
        has_hybrid_tables=False,
        parameters=[],
        query_reduction_settings=QueryReductionConfig(),
        collected_at=datetime.now(UTC),
    )
