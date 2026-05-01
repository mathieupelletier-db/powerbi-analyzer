from powerbi_analyzer.domain.finding import Finding, Phase, Severity, Status


def test_passed_factory_uses_pass_severity():
    f = Finding.passed("RD-005", "Avoid m2m", phase=Phase.REPORT_DESIGN, target="Sales.pbix")
    assert f.status is Status.PASS
    assert f.severity is Severity.PASS
    assert f.rule_id == "RD-005"


def test_failed_factory_uses_declared_severity():
    f = Finding.failed(
        "RD-005",
        "Avoid m2m",
        phase=Phase.REPORT_DESIGN,
        target="Sales.pbix",
        severity=Severity.WARN,
        summary="2 m2m relationships",
        evidence={"relationships": ["A↔B", "C↔D"]},
        why="adds bridge complexity",
        fix="use a bridge dimension",
    )
    assert f.status is Status.FAIL
    assert f.severity is Severity.WARN
    assert f.evidence["relationships"] == ["A↔B", "C↔D"]


def test_not_applicable_factory_uses_na_severity():
    f = Finding.not_applicable(
        "DP-001",
        "Medallion",
        phase=Phase.DATA_PREP,
        target="-",
        reason="mode A cannot inspect catalog",
    )
    assert f.status is Status.NOT_APPLICABLE
    assert f.severity is Severity.NA
    assert "mode A" in f.summary
