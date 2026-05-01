from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.report_design import avoid_many_to_many as rule
from tests.builders import make_relationship, make_semantic_model


def _model(*relationships):
    return make_semantic_model(relationships=list(relationships))


def test_passes_when_no_relationships():
    assert rule.check(_model()).status is Status.PASS


def test_passes_when_only_one_to_many():
    r = make_relationship(cardinality="one-to-many")
    assert rule.check(_model(r)).status is Status.PASS


def test_fails_with_one_many_to_many():
    r = make_relationship(cardinality="many-to-many", from_table="A", to_table="B")
    f = rule.check(_model(r))
    assert f.status is Status.FAIL
    assert "1 many-to-many" in f.summary
    assert "A↔B" in f.evidence["relationships"][0]


def test_fails_with_multiple_many_to_many():
    r1 = make_relationship(cardinality="many-to-many", from_table="A", to_table="B")
    r2 = make_relationship(cardinality="many-to-many", from_table="C", to_table="D")
    f = rule.check(_model(r1, r2))
    assert "2 many-to-many" in f.summary
    assert len(f.evidence["relationships"]) == 2
