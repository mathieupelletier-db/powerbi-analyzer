"""Engine: orchestrate collector outputs through the rule registry into findings."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from powerbi_analyzer.domain.finding import Finding, Phase, Severity, Status
from powerbi_analyzer.rules._registry import RuleRegistry, RuleSpec

log = logging.getLogger(__name__)

_PHASE_ORDER = {
    Phase.DATA_PREP: 0,
    Phase.SQL_SERVING: 1,
    Phase.INTEGRATION: 2,
    Phase.REPORT_DESIGN: 3,
}
_SEVERITY_ORDER = {
    Severity.ERROR: 0,
    Severity.WARN: 1,
    Severity.INFO: 2,
    Severity.PASS: 3,
    Severity.NA: 4,
}


@dataclass(frozen=True)
class PhaseScore:
    phase: Phase
    score: int
    pass_: int
    warn: int
    error: int
    info: int
    na: int


@dataclass(frozen=True)
class RunResult:
    findings: list[Finding]
    phase_scores: dict[Phase, PhaseScore]
    overall_score: int
    errors: list[str] = field(default_factory=list)


class Engine:
    def __init__(self, registry: RuleRegistry) -> None:
        self._registry = registry

    def run(
        self,
        *,
        active_modes: set[str],
        context: dict[type, Any],
        ignore: set[str] | None = None,
        only: set[str] | None = None,
    ) -> RunResult:
        findings: list[Finding] = []
        for spec in self._registry.specs:
            if ignore and spec.rule_id in ignore:
                continue
            if only and spec.rule_id not in only:
                continue
            findings.append(self._run_one(spec, active_modes, context))
        findings.sort(key=lambda f: (_PHASE_ORDER[f.phase], _SEVERITY_ORDER[f.severity], f.rule_id))
        scores = self._score(findings)
        overall = self._overall(scores) if scores else 100
        return RunResult(findings=findings, phase_scores=scores, overall_score=overall)

    def _run_one(self, spec: RuleSpec, active_modes: set[str], context: dict[type, Any]) -> Finding:
        if not (set(spec.applies_to) & active_modes):
            return Finding.not_applicable(
                spec.rule_id,
                spec.name,
                phase=spec.phase,
                target="-",
                reason=f"requires modes {spec.applies_to} but active modes are {sorted(active_modes)}",
                docs_url=spec.docs_url,
            )
        try:
            args: list[Any] = []
            for ptype in spec.parameter_types:
                if ptype not in context:
                    return Finding.not_applicable(
                        spec.rule_id,
                        spec.name,
                        phase=spec.phase,
                        target="-",
                        reason=f"required input {ptype.__name__} not collected",
                        docs_url=spec.docs_url,
                    )
                args.append(context[ptype])
            return spec.check(*args)
        except Exception as exc:
            log.exception("rule %s crashed", spec.rule_id)
            return Finding(
                rule_id=spec.rule_id,
                rule_name=spec.name,
                phase=spec.phase,
                severity=Severity.ERROR,
                status=Status.FAIL,
                summary=f"Rule crashed: {exc}",
                evidence={"exception_type": type(exc).__name__},
                why="The rule raised an unexpected exception while evaluating.",
                fix="File a bug. Re-running with --verbose may surface a stack trace.",
                docs_url=spec.docs_url,
                target="-",
            )

    @staticmethod
    def _score(findings: list[Finding]) -> dict[Phase, PhaseScore]:
        weight = {Severity.ERROR: 3, Severity.WARN: 2, Severity.INFO: 1}
        per_phase: dict[Phase, list[Finding]] = {p: [] for p in Phase}
        for f in findings:
            per_phase[f.phase].append(f)
        out: dict[Phase, PhaseScore] = {}
        for phase, items in per_phase.items():
            considered = [f for f in items if f.status is not Status.NOT_APPLICABLE]
            if not considered:
                continue
            max_score = sum(
                weight.get(f.severity, 0) for f in considered if f.status is Status.FAIL
            ) + sum(weight.get(f.severity, 1) for f in considered if f.status is Status.PASS)
            failed = sum(weight.get(f.severity, 0) for f in considered if f.status is Status.FAIL)
            denom = max(1, max_score)
            score = max(0, round(100 * (denom - failed) / denom))
            out[phase] = PhaseScore(
                phase=phase,
                score=score,
                pass_=sum(1 for f in considered if f.status is Status.PASS),
                error=sum(
                    1
                    for f in considered
                    if f.severity is Severity.ERROR and f.status is Status.FAIL
                ),
                warn=sum(
                    1 for f in considered if f.severity is Severity.WARN and f.status is Status.FAIL
                ),
                info=sum(
                    1 for f in considered if f.severity is Severity.INFO and f.status is Status.FAIL
                ),
                na=sum(1 for f in items if f.status is Status.NOT_APPLICABLE),
            )
        return out

    @staticmethod
    def _overall(scores: dict[Phase, PhaseScore]) -> int:
        if not scores:
            return 100
        return round(sum(s.score for s in scores.values()) / len(scores))
