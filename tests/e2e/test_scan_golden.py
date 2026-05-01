import re
from datetime import UTC, datetime
from pathlib import Path

from powerbi_analyzer.domain.catalog import CatalogState
from powerbi_analyzer.domain.semantic_model import SemanticModel, WorkspaceConfig
from powerbi_analyzer.domain.warehouse import WarehouseState
from powerbi_analyzer.engine import Engine
from powerbi_analyzer.reporters.markdown import MarkdownReporter
from powerbi_analyzer.rules import RuleRegistry

from tests.builders import (
    make_catalog_state,
    make_semantic_model,
    make_table_metadata,
    make_warehouse,
    make_workspace_config,
)

GOLDEN = Path(__file__).parent.parent / "golden" / "scan_all.md.golden"

RUN_ID = re.compile(r"\b[0-9a-f]{6,32}\b")


def _normalize(s: str) -> str:
    return RUN_ID.sub("RUNID", s).strip()


def test_scan_all_golden():
    sm = make_semantic_model(name="Sales")
    wh = make_warehouse(name="bi-prod")
    cat = make_catalog_state(
        tables=[make_table_metadata(full_name="main.gold.fact_sales")],
        referenced_by_powerbi=["main.gold.fact_sales"],
    )
    cfg = make_workspace_config(workspace_id="ws-1")
    engine = Engine(RuleRegistry.discover())
    result = engine.run(
        active_modes={"pbix", "workspace", "databricks"},
        context={SemanticModel: sm, WarehouseState: wh, CatalogState: cat, WorkspaceConfig: cfg},
    )
    md = MarkdownReporter().render(
        result,
        target_description="goldens",
        modes_run=["pbix", "workspace", "databricks"],
        generated_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        version="0.1.0",
    )
    if not GOLDEN.exists() or "PBA_UPDATE_GOLDENS" in __import__("os").environ:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(md)
    assert _normalize(md) == _normalize(GOLDEN.read_text())
