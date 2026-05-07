from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.domain.semantic_model import CalculatedColumn, CalculatedTable
from powerbi_analyzer.rules.report_design import avoid_dax_calc_columns as rule
from tests.builders import make_semantic_model


def test_passes_when_none():
    assert rule.check(make_semantic_model()).status is Status.PASS


def test_fails_with_calc_column():
    m = make_semantic_model(
        calculated_columns=[
            CalculatedColumn(
                name="x",
                table="T",
                expression="1",
                data_type="int64",
            )
        ]
    )
    assert rule.check(m).status is Status.FAIL


def test_fails_with_calc_table():
    m = make_semantic_model(calculated_tables=[CalculatedTable(name="T", expression='ROW("a",1)')])
    assert rule.check(m).status is Status.FAIL
