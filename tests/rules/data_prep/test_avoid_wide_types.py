from powerbi_analyzer.domain.catalog import ColumnMetadata
from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.data_prep import avoid_wide_types as rule
from tests.builders import make_catalog_state, make_table_metadata, make_warehouse


def _t(full_name, columns):
    return make_table_metadata(full_name=full_name, columns=columns)


def _c(name, dt, max_len=None):
    return ColumnMetadata(name=name, data_type=dt, is_nullable=True, max_length_observed=max_len)


def test_passes_when_narrow_types():
    cat = make_catalog_state(
        tables=[_t("main.gold.t", [_c("id", "bigint"), _c("name", "string", 200)])],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.PASS


def test_fails_for_binary():
    cat = make_catalog_state(
        tables=[_t("main.gold.t", [_c("blob", "binary")])],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.FAIL


def test_fails_for_long_string():
    cat = make_catalog_state(
        tables=[_t("main.gold.t", [_c("note", "string", 5000)])],
        referenced_by_powerbi=["main.gold.t"],
    )
    assert rule.check(cat, make_warehouse()).status is Status.FAIL
