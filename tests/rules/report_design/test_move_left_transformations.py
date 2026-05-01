from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import Partition
from powerbi_analyzer.rules.report_design import move_left_transformations as rule

from tests.builders import make_semantic_model, make_table


def _t(m_expr):
    return make_table(
        name="T", partitions=[Partition(name="P", source_type="m", source_expression=m_expr)]
    )


def test_passes_simple_source():
    assert (
        rule.check(make_semantic_model(tables=[_t('Sql.Database("x", "y")')])).status is Status.PASS
    )


def test_fails_when_table_group_present():
    assert (
        rule.check(make_semantic_model(tables=[_t("Table.Group(Source, ...)")])).status
        is Status.FAIL
    )


def test_fails_when_table_nestedjoin():
    assert (
        rule.check(make_semantic_model(tables=[_t("Table.NestedJoin(a, b, ...)")])).status
        is Status.FAIL
    )
