"""Rules that depend on Power BI → table attribution must not silently PASS without it."""

from typing import Any

import pytest

from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.rules import RuleRegistry
from tests.builders import make_catalog_state, make_query, make_table_metadata, make_warehouse

# Rules that read CatalogState.referenced_by_powerbi.
CATALOG_RULES = ["DP-001", "DP-004", "DP-005", "DP-007", "DP-008", "DP-009"]
# Rules that group Power BI queries by QueryHistoryEntry.referenced_tables.
HISTORY_RULES = ["DP-003", "DP-006", "DP-010", "SS-007"]

LINEAGE_ERROR = "PERMISSION_DENIED: system.access.table_lineage"


def _run(rule_id: str, catalog: CatalogState, warehouse: WarehouseState) -> Any:
    spec = RuleRegistry.discover().by_id(rule_id)
    inputs = {CatalogState: catalog, WarehouseState: warehouse}
    return spec.check(*(inputs[t] for t in spec.parameter_types))


def _pbi_history() -> list[Any]:
    return [
        make_query(query_id=f"q{i}", referenced_tables=["main.gold.fact_sales"]) for i in range(6)
    ]


@pytest.mark.parametrize("rule_id", CATALOG_RULES + HISTORY_RULES)
def test_not_applicable_when_lineage_unavailable(rule_id: str) -> None:
    cat = make_catalog_state(tables=[make_table_metadata(full_name="main.gold.fact_sales")])
    wh = make_warehouse(
        query_history=[make_query(query_id=f"q{i}") for i in range(6)],
        table_lineage_error=LINEAGE_ERROR,
    )
    finding = _run(rule_id, cat, wh)
    assert finding.status is Status.NOT_APPLICABLE
    assert "system.access.table_lineage" in finding.summary


@pytest.mark.parametrize("rule_id", CATALOG_RULES)
def test_not_applicable_when_no_powerbi_tables_observed(rule_id: str) -> None:
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.fact_sales")],
        referenced_by_powerbi=[],
    )
    finding = _run(rule_id, cat, make_warehouse())
    assert finding.status is Status.NOT_APPLICABLE
    assert "no Power BI queries" in finding.summary


@pytest.mark.parametrize("rule_id", CATALOG_RULES + HISTORY_RULES)
def test_evaluated_when_attribution_present(rule_id: str) -> None:
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.fact_sales")],
        referenced_by_powerbi=["main.gold.fact_sales"],
    )
    wh = make_warehouse(query_history=_pbi_history())
    finding = _run(rule_id, cat, wh)
    assert finding.status in (Status.PASS, Status.FAIL)


@pytest.mark.parametrize("rule_id", HISTORY_RULES)
def test_not_applicable_when_lineage_attributes_no_powerbi_query(rule_id: str) -> None:
    # Lineage readable but empty for every PBI statement (lag, SHOW/SET statements, ...).
    wh = make_warehouse(query_history=[make_query(query_id=f"q{i}") for i in range(6)])
    finding = _run(rule_id, make_catalog_state(), wh)
    assert finding.status is Status.NOT_APPLICABLE
    assert "no tables" in finding.summary


def test_dp006_ignores_unattributed_queries_when_others_are_attributed() -> None:
    history = [make_query(query_id=f"u{i}") for i in range(6)] + [
        make_query(query_id="a1", referenced_tables=["main.gold.fact_sales"])
    ]
    finding = _run("DP-006", make_catalog_state(), make_warehouse(query_history=history))
    assert finding.status is Status.PASS
