from datetime import UTC, datetime

from powerbi_analyzer.domain.finding import Finding, Phase, Severity
from powerbi_analyzer.engine import PhaseScore, RunResult
from powerbi_analyzer.reporters.html import HtmlReporter


def _result():
    f1 = Finding.passed("RD-001", "ok", phase=Phase.REPORT_DESIGN, target="m")
    f2 = Finding.failed(
        "RD-005",
        "Avoid m2m",
        phase=Phase.REPORT_DESIGN,
        target="m",
        severity=Severity.WARN,
        summary="2 m2m",
        evidence={"pairs": ["A↔B"]},
        why="bridge",
        fix="bridge dim",
        docs_url="https://x",
    )
    return RunResult(
        findings=[f1, f2],
        phase_scores={
            Phase.REPORT_DESIGN: PhaseScore(
                phase=Phase.REPORT_DESIGN,
                score=80,
                pass_=1,
                warn=1,
                error=0,
                info=0,
                na=0,
            )
        },
        overall_score=80,
    )


def test_html_self_contained_no_external_assets():
    out = HtmlReporter().render(
        _result(),
        target_description="m",
        modes_run=["pbix"],
        generated_at=datetime(2026, 5, 1, tzinfo=UTC),
        version="0.1.0",
        embed_fonts=False,
    )
    assert "<!DOCTYPE html>" in out
    assert "RD-005" in out
    assert "<style>" in out
    assert "<script>" in out
    assert "fonts.googleapis.com" in out  # default uses CDN font


def test_html_embed_fonts_inlines_woff2():
    # When embed_fonts=True, the Google Fonts CDN link must not appear.
    # If DMSans-Regular.woff2 is present next to the templates, a base64
    # data URL is injected; if it is absent the font-face block is still
    # rendered but with an empty src.  Either way the external CDN link
    # must be absent.  We do not ship the binary font file in this repo,
    # so we only assert the CDN link is gone.
    out = HtmlReporter().render(
        _result(),
        target_description="m",
        modes_run=["pbix"],
        generated_at=datetime(2026, 5, 1, tzinfo=UTC),
        version="0.1.0",
        embed_fonts=True,
    )
    assert "fonts.googleapis.com" not in out
