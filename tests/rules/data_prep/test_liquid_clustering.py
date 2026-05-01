from powerbi_analyzer.domain.catalog import ClusteringInfo
from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.data_prep import liquid_clustering as rule

from tests.builders import make_catalog_state, make_table_metadata, make_warehouse


def test_passes_when_clustered():
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.t",
                clustering=ClusteringInfo(kind="liquid", columns=["id"]),
                size_bytes=20 * 1024**3,
            )
        ],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS


def test_fails_when_large_unclustered():
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.t",
                clustering=ClusteringInfo(kind="none", columns=[]),
                size_bytes=20 * 1024**3,
            )
        ],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.FAIL


def test_passes_small_unclustered():
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.t",
                clustering=ClusteringInfo(kind="none", columns=[]),
                size_bytes=1 * 1024**3,
            )
        ],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS


def test_passes_when_no_referenced_tables():
    cat = make_catalog_state(
        tables=[
            make_table_metadata(
                full_name="main.gold.t",
                clustering=ClusteringInfo(kind="none", columns=[]),
                size_bytes=20 * 1024**3,
            )
        ],
        referenced_by_powerbi=[],
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS
