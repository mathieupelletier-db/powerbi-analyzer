from powerbi_analyzer.domain.finding import Finding, Phase, Severity, Status
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.engine import Engine
from powerbi_analyzer.rules import RuleRegistry
from powerbi_analyzer.rules._registry import RuleSpec

from tests.builders import make_semantic_model, make_warehouse


def _spec(
    rule_id, applies_to, parameter_types, fn, severity=Severity.WARN, phase=Phase.REPORT_DESIGN
):
    return RuleSpec(
        rule_id=rule_id,
        name=rule_id,
        phase=phase,
        severity=severity,
        applies_to=applies_to,
        docs_url="x",
        parameter_types=parameter_types,
        check=fn,
        module_path="t",
    )


def test_engine_runs_applicable_rule():
    def check(model: SemanticModel) -> Finding:
        return Finding.passed("RD-001", "x", phase=Phase.REPORT_DESIGN, target=model.name)

    spec = _spec("RD-001", ["pbix"], [SemanticModel], check)
    reg = RuleRegistry(specs=[spec])
    engine = Engine(reg)
    result = engine.run(
        active_modes={"pbix"}, context={SemanticModel: make_semantic_model(name="m1")}
    )
    assert len(result.findings) == 1
    assert result.findings[0].status is Status.PASS


def test_engine_skips_inapplicable_rule():
    def check(model: SemanticModel) -> Finding:
        raise AssertionError("should not run")

    spec = _spec("RD-001", ["workspace"], [SemanticModel], check)
    engine = Engine(RuleRegistry(specs=[spec]))
    result = engine.run(active_modes={"databricks"}, context={})
    assert result.findings[0].status is Status.NOT_APPLICABLE


def test_engine_converts_exception_to_error_finding():
    def check(model: SemanticModel) -> Finding:
        raise RuntimeError("boom")

    spec = _spec("RD-001", ["pbix"], [SemanticModel], check)
    engine = Engine(RuleRegistry(specs=[spec]))
    result = engine.run(active_modes={"pbix"}, context={SemanticModel: make_semantic_model()})
    f = result.findings[0]
    assert f.status is Status.FAIL
    assert f.severity is Severity.ERROR
    assert "boom" in f.summary


def test_engine_multi_param_rule_resolves_from_context():
    from powerbi_analyzer.domain.warehouse import WarehouseState

    def check(model: SemanticModel, wh: WarehouseState) -> Finding:
        return Finding.passed("IN-001", "region", phase=Phase.INTEGRATION, target=wh.region)

    spec = _spec(
        "IN-001",
        ["workspace", "databricks"],
        [SemanticModel, WarehouseState],
        check,
        phase=Phase.INTEGRATION,
    )
    engine = Engine(RuleRegistry(specs=[spec]))
    result = engine.run(
        active_modes={"workspace", "databricks"},
        context={SemanticModel: make_semantic_model(), WarehouseState: make_warehouse()},
    )
    assert result.findings[0].status is Status.PASS


def test_engine_findings_sorted_by_phase_severity_id():
    def make(rule_id, phase, severity):
        def check() -> Finding:
            return Finding.failed(
                rule_id,
                rule_id,
                phase=phase,
                target="-",
                severity=severity,
                summary="s",
                evidence={},
                why="w",
                fix="f",
            )

        return _spec(rule_id, ["databricks"], [], check, severity=severity, phase=phase)

    specs = [
        make("DP-002", Phase.DATA_PREP, Severity.WARN),
        make("DP-001", Phase.DATA_PREP, Severity.ERROR),
        make("RD-001", Phase.REPORT_DESIGN, Severity.WARN),
    ]
    engine = Engine(RuleRegistry(specs=specs))
    result = engine.run(active_modes={"databricks"}, context={})
    ids = [f.rule_id for f in result.findings]
    assert ids == ["DP-001", "DP-002", "RD-001"]
