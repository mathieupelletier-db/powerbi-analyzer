"""HTML report renderer — single self-contained file."""

from __future__ import annotations

import base64
from datetime import datetime
from importlib import resources
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from powerbi_analyzer.domain.finding import Phase
from powerbi_analyzer.engine import RunResult

_PHASE_LABEL = {
    Phase.DATA_PREP: "Data Preparation",
    Phase.SQL_SERVING: "SQL Serving",
    Phase.INTEGRATION: "Power BI Integration",
    Phase.REPORT_DESIGN: "Power BI Report Design",
}

_SEV_ORDER = ["error", "warn", "info", "pass", "na"]


class HtmlReporter:
    def __init__(self) -> None:
        templates_dir = Path(resources.files("powerbi_analyzer.reporters") / "templates")  # type: ignore[arg-type]
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self._templates_dir = templates_dir

    def render(
        self,
        result: RunResult,
        *,
        target_description: str,
        modes_run: list[str],
        generated_at: datetime,
        version: str,
        embed_fonts: bool = False,
    ) -> str:
        css = (self._templates_dir / "report.css").read_text()
        js = (self._templates_dir / "report.js").read_text()
        font_b64 = ""
        if embed_fonts:
            font_path = self._templates_dir / "DMSans-Regular.woff2"
            if font_path.exists():
                font_b64 = base64.b64encode(font_path.read_bytes()).decode()
        scores = [
            (_PHASE_LABEL[p], result.phase_scores[p]) for p in Phase if p in result.phase_scores
        ]
        by_phase = []
        for p in Phase:
            items = sorted(
                [f for f in result.findings if f.phase is p],
                key=lambda f: (
                    _SEV_ORDER.index(str(f.severity))
                    if str(f.severity) in _SEV_ORDER
                    else len(_SEV_ORDER),
                    f.rule_id,
                ),
            )
            if items:
                by_phase.append((_PHASE_LABEL[p], items))
        rendered: str = self._env.get_template("report.html.j2").render(
            target=target_description,
            modes=", ".join(modes_run),
            generated_at=generated_at.strftime("%Y-%m-%d %H:%M %Z"),
            version=version,
            scores=scores,
            overall=result.overall_score,
            by_phase=by_phase,
            css=css,
            js=js,
            embed_fonts=embed_fonts,
            font_b64=font_b64,
        )
        return rendered
