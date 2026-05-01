from powerbi_analyzer.domain.finding import Status
from powerbi_analyzer.rules.report_design import assume_referential_integrity as rule

from tests.builders import make_column, make_relationship, make_semantic_model, make_table


def test_passes_when_ari_set():
    t = make_table(name="F", columns=[make_column(name="cid", is_nullable=False)])
    r = make_relationship(
        from_table="F",
        from_column="cid",
        to_table="D",
        to_column="id",
        cardinality="many-to-one",
        assume_referential_integrity=True,
    )
    assert rule.check(make_semantic_model(tables=[t], relationships=[r])).status is Status.PASS


def test_fails_when_not_null_without_ari():
    t = make_table(name="F", columns=[make_column(name="cid", is_nullable=False)])
    r = make_relationship(
        from_table="F",
        from_column="cid",
        to_table="D",
        to_column="id",
        cardinality="many-to-one",
        assume_referential_integrity=False,
    )
    assert rule.check(make_semantic_model(tables=[t], relationships=[r])).status is Status.FAIL


def test_passes_when_nullable():
    t = make_table(name="F", columns=[make_column(name="cid", is_nullable=True)])
    r = make_relationship(
        from_table="F",
        from_column="cid",
        to_table="D",
        to_column="id",
        cardinality="many-to-one",
        assume_referential_integrity=False,
    )
    assert rule.check(make_semantic_model(tables=[t], relationships=[r])).status is Status.PASS
