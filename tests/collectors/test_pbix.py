# tests/collectors/test_pbix.py
"""Tests for PbixCollector — .pbip fixtures + mocked pbixray for .pbix path."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from powerbi_analyzer.collectors.pbix import PbixCollector
from powerbi_analyzer.domain.semantic_model import SemanticModel

FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbix"


# ---------------------------------------------------------------------------
# .pbip fixtures
# ---------------------------------------------------------------------------


def test_collect_small_good_pbip_returns_semantic_model() -> None:
    sm: SemanticModel = PbixCollector(path=FIXTURES / "small_good.pbip").collect()
    assert sm.source == "pbip"
    names = {t.name for t in sm.tables}
    assert {"Fact_Sales", "Dim_Customer"} <= names
    # One many-to-one relationship
    assert any(r.cardinality == "many-to-one" for r in sm.relationships)
    # No many-to-many
    assert not any(r.cardinality == "many-to-many" for r in sm.relationships)
    # TotalRevenue measure present
    assert any(m.name == "TotalRevenue" for m in sm.measures)
    # No calculated columns
    assert not sm.calculated_columns


def test_collect_small_bad_pbip_has_many_to_many() -> None:
    sm: SemanticModel = PbixCollector(path=FIXTURES / "small_bad.pbip").collect()
    assert sm.source == "pbip"
    # Has a many-to-many relationship (RD-005 trigger)
    assert any(r.cardinality == "many-to-many" for r in sm.relationships), (
        "small_bad should have a many-to-many relationship"
    )
    # Has a calculated column (RD-011 trigger)
    assert sm.calculated_columns, "small_bad should declare a calculated column"


def test_collect_missing_path_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        PbixCollector(path=FIXTURES / "does_not_exist.pbix").collect()


# ---------------------------------------------------------------------------
# .pbix path via mocked pbixray
# ---------------------------------------------------------------------------


def _make_mock_ray(
    *,
    tables: list[str],
    relationships: list[dict],
    dax_measures: list[dict],
    dax_columns: list[dict],
    dax_tables: list[dict],
) -> MagicMock:
    mock = MagicMock()
    mock.tables = tables
    mock.relationships = relationships
    mock.dax_measures = dax_measures
    mock.dax_columns = dax_columns
    mock.dax_tables = dax_tables
    mock.statistics = {}
    # schema() returns an empty list for each table (no column detail)
    mock.schema.return_value = []
    return mock


def test_collect_pbix_good_via_mock(tmp_path: Path) -> None:
    fake_pbix = tmp_path / "model.pbix"
    fake_pbix.write_bytes(b"PK")  # minimal non-empty file

    mock_ray = _make_mock_ray(
        tables=["Fact_Sales", "Dim_Customer"],
        relationships=[
            {
                "FromTable": "Fact_Sales",
                "FromColumn": "CustomerId",
                "ToTable": "Dim_Customer",
                "ToColumn": "CustomerId",
                "Cardinality": "ManyToOne",
                "CrossFilter": "OneDirection",
                "IsActive": True,
                "RelyOnReferentialIntegrity": True,
            }
        ],
        dax_measures=[
            {
                "Name": "TotalRevenue",
                "Table": "Fact_Sales",
                "Expression": "SUM(Fact_Sales[Revenue])",
                "FormatString": None,
            }
        ],
        dax_columns=[],
        dax_tables=[],
    )

    with patch("powerbi_analyzer.collectors.pbix.PBIXRay", return_value=mock_ray):
        sm: SemanticModel = PbixCollector(path=fake_pbix).collect()

    assert sm.source == "pbix"
    assert {t.name for t in sm.tables} == {"Fact_Sales", "Dim_Customer"}
    assert any(r.cardinality == "many-to-one" for r in sm.relationships)
    assert any(m.name == "TotalRevenue" for m in sm.measures)


def test_collect_pbix_bad_via_mock(tmp_path: Path) -> None:
    fake_pbix = tmp_path / "model.pbix"
    fake_pbix.write_bytes(b"PK")

    mock_ray = _make_mock_ray(
        tables=["Fact_Sales"],
        relationships=[
            {
                "FromTable": "Fact_Sales",
                "FromColumn": "Region",
                "ToTable": "Dim_Region",
                "ToColumn": "RegionId",
                "Cardinality": "ManyToMany",
                "CrossFilter": "BothDirections",
                "IsActive": True,
                "RelyOnReferentialIntegrity": False,
            }
        ],
        dax_measures=[],
        dax_columns=[
            {
                "Name": "RevenuePlus10",
                "Table": "Fact_Sales",
                "Expression": "Fact_Sales[Revenue] * 1.1",
                "DataType": "decimal",
            }
        ],
        dax_tables=[],
    )

    with patch("powerbi_analyzer.collectors.pbix.PBIXRay", return_value=mock_ray):
        sm: SemanticModel = PbixCollector(path=fake_pbix).collect()

    assert any(r.cardinality == "many-to-many" for r in sm.relationships)
    assert sm.calculated_columns
