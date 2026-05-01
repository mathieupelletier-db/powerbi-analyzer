"""Rule discovery, validation, and storage.

Rules are simple modules under powerbi_analyzer.rules.<phase>.<name> that declare
required constants and a `check(...)` function. The registry validates the
contract on import and exposes typed metadata to the engine.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from powerbi_analyzer.domain.finding import Finding, Phase, Severity

REQUIRED_CONSTANTS = ("RULE_ID", "NAME", "PHASE", "SEVERITY", "APPLIES_TO", "DOCS_URL")
PHASE_PREFIX = {
    Phase.DATA_PREP: "DP",
    Phase.SQL_SERVING: "SS",
    Phase.INTEGRATION: "IN",
    Phase.REPORT_DESIGN: "RD",
}
RULE_ID_PATTERN = re.compile(r"^(DP|SS|IN|RD)-\d{3}$")
SKIP_MARKER = "# pba: skip"


def rule(rule_id: str) -> Callable[[Callable[..., Finding]], Callable[..., Finding]]:
    """Marker decorator. Currently a no-op tag — kept so we can add tracing later."""

    def wrap(fn: Callable[..., Finding]) -> Callable[..., Finding]:
        fn.__pba_rule_id__ = rule_id  # type: ignore[attr-defined]
        return fn

    return wrap


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    name: str
    phase: Phase
    severity: Severity
    applies_to: list[str]
    docs_url: str
    parameter_types: list[type]
    check: Callable[..., Finding]
    module_path: str


def file_has_skip_marker(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return any(line.strip().startswith(SKIP_MARKER) for line in text.splitlines()[:5])


def load_module_as_rule(module: ModuleType) -> RuleSpec:
    missing = [c for c in REQUIRED_CONSTANTS if not hasattr(module, c)]
    if missing:
        raise ValueError(
            f"{module.__name__}: missing required constants {missing} (need {list(REQUIRED_CONSTANTS)})"
        )
    rule_id = module.RULE_ID
    if not RULE_ID_PATTERN.match(rule_id):
        raise ValueError(
            f"{module.__name__}: RULE_ID '{rule_id}' has invalid prefix;"
            f" must match {RULE_ID_PATTERN.pattern}"
        )
    phase = module.PHASE
    if not isinstance(phase, Phase):
        raise ValueError(f"{module.__name__}: PHASE must be a Phase enum, got {type(phase)}")
    expected_prefix = PHASE_PREFIX[phase]
    if not rule_id.startswith(expected_prefix + "-"):
        raise ValueError(
            f"{module.__name__}: RULE_ID prefix '{rule_id[:2]}' does not match phase {phase}"
            f" (expected '{expected_prefix}-')"
        )
    severity = module.SEVERITY
    if severity not in (Severity.ERROR, Severity.WARN, Severity.INFO):
        raise ValueError(f"{module.__name__}: SEVERITY must be ERROR/WARN/INFO; got {severity}")
    applies_to = list(module.APPLIES_TO)
    valid_modes = {"pbix", "pbip", "workspace", "databricks"}
    bad = [m for m in applies_to if m not in valid_modes]
    if bad:
        raise ValueError(f"{module.__name__}: invalid APPLIES_TO entries {bad}")
    docs_url = module.DOCS_URL
    if not isinstance(docs_url, str) or not docs_url:
        raise ValueError(f"{module.__name__}: DOCS_URL must be a non-empty string")
    check: Any = getattr(module, "check", None)
    if not callable(check):
        raise ValueError(f"{module.__name__}: must define a callable check(...)")
    sig = inspect.signature(check)
    parameter_types: list[type] = []
    for param in sig.parameters.values():
        if param.annotation is inspect.Parameter.empty:
            raise ValueError(
                f"{module.__name__}: check() parameter '{param.name}' missing type annotation"
            )
        parameter_types.append(param.annotation)
    return RuleSpec(
        rule_id=rule_id,
        name=module.NAME,
        phase=phase,
        severity=severity,
        applies_to=applies_to,
        docs_url=docs_url,
        parameter_types=parameter_types,
        check=check,
        module_path=module.__name__,
    )


@dataclass
class RuleRegistry:
    specs: list[RuleSpec] = field(default_factory=list)

    @classmethod
    def discover(cls, package: str = "powerbi_analyzer.rules") -> RuleRegistry:
        registry = cls()
        pkg = importlib.import_module(package)
        for _finder, modname, ispkg in pkgutil.walk_packages(pkg.__path__, prefix=f"{package}."):
            if modname.rsplit(".", 1)[-1].startswith("_"):
                continue
            if ispkg:
                continue
            module = importlib.import_module(modname)
            origin = getattr(module, "__file__", None)
            if origin and file_has_skip_marker(Path(origin)):
                continue
            spec = load_module_as_rule(module)
            registry.add(spec)
        return registry

    def add(self, spec: RuleSpec) -> None:
        if any(s.rule_id == spec.rule_id for s in self.specs):
            raise ValueError(f"duplicate RULE_ID '{spec.rule_id}'")
        self.specs.append(spec)

    def by_id(self, rule_id: str) -> RuleSpec:
        for s in self.specs:
            if s.rule_id == rule_id:
                return s
        raise KeyError(rule_id)

    def filter(
        self,
        *,
        active_modes: set[str] | None = None,
        ignore: set[str] | None = None,
        only: set[str] | None = None,
    ) -> list[RuleSpec]:
        out: list[RuleSpec] = []
        for s in self.specs:
            if ignore and s.rule_id in ignore:
                continue
            if only and s.rule_id not in only:
                continue
            if active_modes is not None and not (set(s.applies_to) & active_modes):
                continue
            out.append(s)
        return out
