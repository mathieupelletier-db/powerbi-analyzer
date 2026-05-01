"""Markdown report renderer."""

from __future__ import annotations

import json
from datetime import datetime
from textwrap import dedent

from powerbi_analyzer.domain.finding import Finding, Phase, Severity, Status
from powerbi_analyzer.engine import PhaseScore, RunResult

_PHASE_LABEL = {
    Phase.DATA_PREP: "Data Preparation",
    Phase.SQL_SERVING: "SQL Serving",
    Phase.INTEGRATION: "Power BI Integration",
    Phase.REPORT_DESIGN: "Power BI Report Design",
}
_SEV_ICON = {
    Severity.ERROR: "❌",
    Severity.WARN: "⚠️",
    Severity.INFO: "ℹ️",  # noqa: RUF001
    Severity.PASS: "✅",
    Severity.NA: "—",
}
_SEV_ORDER = [Severity.ERROR, Severity.WARN, Severity.INFO, Severity.PASS, Severity.NA]


class MarkdownReporter:
    def render(
        self,
        result: RunResult,
        *,
        target_description: str,
        modes_run: list[str],
        generated_at: datetime,
        version: str,
    ) -> str:
        parts: list[str] = []
        parts.append(f"# Power BI on Databricks Audit — {target_description}\n")
        parts.append(f"Generated {generated_at:%Y-%m-%d %H:%M %Z} by pba {version}\n")
        parts.append(f"Modes run: {', '.join(modes_run)}\n")
        parts.append(self._summary(result))
        for phase in Phase:
            section = self._phase_section(phase, result.findings)
            if section:
                parts.append(section)
        return "\n".join(parts)

    def _summary(self, result: RunResult) -> str:
        lines = [
            "## Summary\n",
            "| Phase | Score | Pass | Warn | Error | Info | N/A |",
            "|---|---|---|---|---|---|---|",
        ]
        for phase in Phase:
            s: PhaseScore | None = result.phase_scores.get(phase)
            if s is None:
                lines.append(f"| {_PHASE_LABEL[phase]} | — | — | — | — | — | — |")
            else:
                lines.append(
                    f"| {_PHASE_LABEL[phase]} | {s.score}/100 | {s.pass_} | {s.warn} "
                    f"| {s.error} | {s.info} | {s.na} |"
                )
        lines.append(f"| **Overall** | **{result.overall_score}/100** | | | | | |\n")
        top = sorted(
            (f for f in result.findings if f.status is Status.FAIL),
            key=lambda f: (
                {Severity.ERROR: 0, Severity.WARN: 1, Severity.INFO: 2}[f.severity],
                f.rule_id,
            ),
        )[:5]
        if top:
            lines.append("### Top 5 highest-impact issues\n")
            for i, f in enumerate(top, 1):
                lines.append(f"{i}. **[{f.rule_id}] {f.rule_name}** ({f.severity}) — {f.summary}")
            lines.append("")
        return "\n".join(lines)

    def _phase_section(self, phase: Phase, findings: list[Finding]) -> str:
        items = [f for f in findings if f.phase is phase]
        if not items:
            return ""
        items.sort(key=lambda f: (_SEV_ORDER.index(f.severity), f.rule_id))
        out = [f"## {_PHASE_LABEL[phase]}\n"]
        for f in items:
            out.append(self._finding(f))
        return "\n".join(out)

    @staticmethod
    def _finding(f: Finding) -> str:
        icon = _SEV_ICON[f.severity]
        header = f"### {icon} {f.rule_id} {f.rule_name} ({f.severity})"
        body = [
            header,
            f"**Target:** {f.target}",
            f"**Status:** {f.status}",
            f"**Summary:** {f.summary}",
        ]
        if f.why:
            body.append(f"**Why it matters:** {f.why}")
        if f.fix:
            body.append(f"**How to fix:** {f.fix}")
        if f.docs_url:
            body.append(f"**Reference:** [{f.docs_url}]({f.docs_url})")
        if f.evidence:
            ev = json.dumps(f.evidence, indent=2, default=str, ensure_ascii=False)
            body.append(
                dedent(f"""\
                <details><summary>Evidence</summary>

                ```json
                {ev}
                ```
                </details>""")
            )
        body.append("")
        return "\n".join(body)
