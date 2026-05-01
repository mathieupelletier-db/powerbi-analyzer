from datetime import UTC, datetime, timedelta

from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.data_prep import optimize_or_predictive as rule

from tests.builders import make_catalog_state, make_table_metadata, make_warehouse


def test_passes_with_predictive_optimization():
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.t",
                predictive_optimization=True,
                last_optimize_at=None,
                last_vacuum_at=None,
            )
        ],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS


def test_passes_recently_optimized():
    now = datetime.now(UTC)
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.t",
                predictive_optimization=False,
                last_optimize_at=now - timedelta(days=5),
                last_vacuum_at=now - timedelta(days=5),
            )
        ],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS


def test_fails_stale_optimize_and_vacuum():
    now = datetime.now(UTC)
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.t",
                predictive_optimization=False,
                last_optimize_at=now - timedelta(days=60),
                last_vacuum_at=now - timedelta(days=60),
            )
        ],
        referenced_by_powerbi=["main.gold.t"],
    )
    f = rule.check(cat, make_warehouse())
    assert f.status is Status.FAIL
    assert "main.gold.t" in f.evidence["tables"]


def test_fails_when_never_optimized():
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.t",
                predictive_optimization=False,
                last_optimize_at=None,
                last_vacuum_at=None,
            )
        ],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.FAIL
