"""Finding — the unit every rule emits.

Severity / status invariants:
- status == PASS            ⇒ severity == PASS
- status == FAIL            ⇒ severity is the rule's declared SEVERITY
- status == NOT_APPLICABLE  ⇒ severity == NA
- status == SKIPPED         ⇒ severity retains the rule's declared value (display only)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    PASS = "pass"
    NA = "n/a"


class Status(StrEnum):
    FAIL = "fail"
    PASS = "pass"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"


class Phase(StrEnum):
    DATA_PREP = "data_prep"
    SQL_SERVING = "sql_serving"
    INTEGRATION = "integration"
    REPORT_DESIGN = "report_design"


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    rule_name: str
    phase: Phase
    severity: Severity
    status: Status
    summary: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    why: str = ""
    fix: str = ""
    docs_url: str | None = None
    target: str = ""

    @classmethod
    def passed(
        cls,
        rule_id: str,
        rule_name: str,
        *,
        phase: Phase,
        target: str,
        summary: str = "Rule passed.",
        docs_url: str | None = None,
    ) -> Self:
        return cls(
            rule_id=rule_id,
            rule_name=rule_name,
            phase=phase,
            severity=Severity.PASS,
            status=Status.PASS,
            summary=summary,
            target=target,
            docs_url=docs_url,
        )

    @classmethod
    def failed(
        cls,
        rule_id: str,
        rule_name: str,
        *,
        phase: Phase,
        target: str,
        severity: Severity,
        summary: str,
        evidence: dict[str, Any] | None = None,
        why: str = "",
        fix: str = "",
        docs_url: str | None = None,
    ) -> Self:
        if severity in (Severity.PASS, Severity.NA):
            raise ValueError(f"failed() requires error/warn/info severity, got {severity}")
        return cls(
            rule_id=rule_id,
            rule_name=rule_name,
            phase=phase,
            severity=severity,
            status=Status.FAIL,
            summary=summary,
            evidence=evidence or {},
            why=why,
            fix=fix,
            docs_url=docs_url,
            target=target,
        )

    @classmethod
    def not_applicable(
        cls,
        rule_id: str,
        rule_name: str,
        *,
        phase: Phase,
        target: str,
        reason: str,
        docs_url: str | None = None,
    ) -> Self:
        return cls(
            rule_id=rule_id,
            rule_name=rule_name,
            phase=phase,
            severity=Severity.NA,
            status=Status.NOT_APPLICABLE,
            summary=f"Not applicable: {reason}",
            target=target,
            docs_url=docs_url,
        )
