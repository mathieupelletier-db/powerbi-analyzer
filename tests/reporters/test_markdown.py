# tests/reporters/test_markdown.py
from datetime import UTC, datetime

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.engine import PhaseScore, RunResult
from powerbi_analyzer.reporters.markdown import MarkdownReporter


def _result(findings):
    scores = {
        Phase.REPORT_DESIGN: PhaseScore(
            phase=Phase.REPORT_DESIGN,
            score=80,
            pass_=1,
            warn=1,
            error=0,
            info=0,
            na=0,
        )
    }
    return RunResult(findings=findings, phase_scores=scores, overall_score=80)


def test_markdown_includes_summary_table_and_findings():
    findings = [
        Finding.passed(
            "RD-001", "Limit visuals", phase=Phase.REPORT_DESIGN, target="Sales.pbix", summary="ok"
        ),
        Finding.failed(
            "RD-005",
            "Avoid m2m",
            phase=Phase.REPORT_DESIGN,
            target="Sales.pbix",
            severity=Severity.WARN,
            summary="2 m2m relationships",
            evidence={"pairs": ["A↔B"]},
            why="bridge complexity",
            fix="use a bridge dim",
            docs_url="https://x",
        ),
    ]
    out = MarkdownReporter().render(
        _result(findings),
        target_description="Sales.pbix",
        modes_run=["pbix"],
        generated_at=datetime(2026, 5, 1, 14, 22, tzinfo=UTC),
        version="0.1.0",
    )
    assert "| Phase " in out
    assert "Score" in out
    assert "RD-001" in out
    assert "Avoid m2m" in out
    assert "<details>" in out
    assert "use a bridge dim" in out
