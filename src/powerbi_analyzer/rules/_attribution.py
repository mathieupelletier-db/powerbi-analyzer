"""Guards for rules that depend on attributing Power BI queries to tables.

Without these, an empty attribution set reads as "nothing wrong" and the rule
PASSes without having checked anything.
"""

from __future__ import annotations

from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.warehouse import WarehouseState, is_powerbi_client


def lineage_gap(warehouse: WarehouseState) -> str | None:
    """Reason to skip when table lineage could not be read, else None."""
    if not warehouse.table_lineage_error:
        return None
    return (
        "Power BI queries could not be attributed to tables — grant SELECT on "
        f"system.access.table_lineage ({warehouse.table_lineage_error})"
    )


def history_gap(warehouse: WarehouseState) -> str | None:
    """Reason to skip query-pattern rules when no Power BI query has known tables, else None."""
    gap = lineage_gap(warehouse)
    if gap:
        return gap
    pbi = [q for q in warehouse.query_history if is_powerbi_client(q.client_application)]
    if pbi and not any(q.referenced_tables for q in pbi):
        return f"table lineage returned no tables for any of the {len(pbi)} Power BI queries"
    return None


def attribution_gap(catalog: CatalogState, warehouse: WarehouseState) -> str | None:
    """Reason to skip when no Power BI-referenced tables are known, else None."""
    gap = lineage_gap(warehouse)
    if gap:
        return gap
    if not catalog.referenced_by_powerbi:
        return "no Power BI queries touched the scanned catalogs in the lookback window"
    return None
