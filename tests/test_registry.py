import importlib
import sys
from types import ModuleType

import pytest
from powerbi_analyzer.domain.finding import Phase, Severity
from powerbi_analyzer.domain.semantic_model import SemanticModel
from powerbi_analyzer.rules._registry import RuleRegistry, load_module_as_rule


def _module_with(**attrs: object) -> ModuleType:
    name = f"test_rule_{id(attrs)}"
    mod = ModuleType(name)

    def check(model: SemanticModel):
        from powerbi_analyzer.domain.finding import Finding

        return Finding.passed(attrs["RULE_ID"], attrs["NAME"], phase=attrs["PHASE"], target="-")  # type: ignore[arg-type]

    mod.check = check  # type: ignore[attr-defined]
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def test_load_module_extracts_rule_spec():
    mod = _module_with(
        RULE_ID="RD-005",
        NAME="Avoid m2m",
        PHASE=Phase.REPORT_DESIGN,
        SEVERITY=Severity.WARN,
        APPLIES_TO=["pbix", "workspace"],
        DOCS_URL="https://example.com/m2m",
    )
    spec = load_module_as_rule(mod)
    assert spec.rule_id == "RD-005"
    assert spec.applies_to == ["pbix", "workspace"]
    assert spec.parameter_types == [SemanticModel]


def test_load_module_missing_constant_raises():
    mod = _module_with(
        RULE_ID="RD-099",
        NAME="x",
        PHASE=Phase.REPORT_DESIGN,
        SEVERITY=Severity.WARN,
        APPLIES_TO=["pbix"],
        # missing DOCS_URL
    )
    with pytest.raises(ValueError, match="DOCS_URL"):
        load_module_as_rule(mod)


def test_load_module_bad_id_prefix_raises():
    mod = _module_with(
        RULE_ID="XX-001",
        NAME="x",
        PHASE=Phase.REPORT_DESIGN,
        SEVERITY=Severity.WARN,
        APPLIES_TO=["pbix"],
        DOCS_URL="https://example.com",
    )
    with pytest.raises(ValueError, match="prefix"):
        load_module_as_rule(mod)


def test_registry_discovers_rules_from_package():
    importlib.import_module("powerbi_analyzer.rules")
    reg = RuleRegistry.discover()
    # No rules implemented yet — but discovery should succeed cleanly
    assert isinstance(reg.specs, list)


def test_registry_rejects_duplicate_rule_id():
    a = _module_with(
        RULE_ID="DP-001",
        NAME="a",
        PHASE=Phase.DATA_PREP,
        SEVERITY=Severity.WARN,
        APPLIES_TO=["databricks"],
        DOCS_URL="x",
    )
    b = _module_with(
        RULE_ID="DP-001",
        NAME="b",
        PHASE=Phase.DATA_PREP,
        SEVERITY=Severity.ERROR,
        APPLIES_TO=["databricks"],
        DOCS_URL="x",
    )
    reg = RuleRegistry(specs=[load_module_as_rule(a)])
    with pytest.raises(ValueError, match="duplicate"):
        reg.add(load_module_as_rule(b))


def test_rule_spec_skipped_via_marker_comment(tmp_path):
    src = tmp_path / "skipped_rule.py"
    src.write_text(
        "# pba: skip\n"
        "from powerbi_analyzer.domain.finding import Phase, Severity\n"
        'RULE_ID = "DP-099"\n'
        'NAME = "x"\n'
        "PHASE = Phase.DATA_PREP\n"
        "SEVERITY = Severity.WARN\n"
        'APPLIES_TO = ["databricks"]\n'
        'DOCS_URL = "x"\n'
        "def check(model): return None\n"
    )
    from powerbi_analyzer.rules._registry import file_has_skip_marker

    assert file_has_skip_marker(src)
