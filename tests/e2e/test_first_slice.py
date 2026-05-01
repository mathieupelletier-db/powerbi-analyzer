from datetime import UTC, datetime

from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.engine import Engine
from powerbi_analyzer.reporters.markdown import MarkdownReporter
from powerbi_analyzer.rules import RuleRegistry

from tests.builders import make_relationship, make_semantic_model


def test_engine_plus_markdown_reporter_renders_finding():
    registry = RuleRegistry.discover()
    assert any(s.rule_id == "RD-005" for s in registry.specs)
    engine = Engine(registry)
    model = make_semantic_model(
        name="Sales",
        relationships=[
            make_relationship(cardinality="many-to-many", from_table="A", to_table="B"),
        ],
    )
    result = engine.run(active_modes={"pbix"}, context={SemanticModel: model})
    md = MarkdownReporter().render(
        result,
        target_description="Sales.pbix",
        modes_run=["pbix"],
        generated_at=datetime(2026, 5, 1, tzinfo=UTC),
        version="0.1.0",
    )
    assert "RD-005" in md
    assert "Avoid many-to-many" in md
    assert "A↔B" in md
