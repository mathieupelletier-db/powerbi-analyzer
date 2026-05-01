"""Pre-commit hook: verify every rule file declares required constants and has a sibling test."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REQUIRED = {"RULE_ID", "NAME", "PHASE", "SEVERITY", "APPLIES_TO", "DOCS_URL"}
RULES_DIR = Path("src/powerbi_analyzer/rules")
TESTS_DIR = Path("tests/rules")


def find_constants(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    found.add(tgt.id)
    return found


def main(argv: list[str]) -> int:
    failures: list[str] = []
    for path_str in argv:
        path = Path(path_str)
        if path.name.startswith("_") or path.parent.name == "rules":
            continue  # registry / __init__ files
        try:
            constants = find_constants(path)
        except SyntaxError as exc:
            failures.append(f"{path}: syntax error: {exc}")
            continue
        missing = REQUIRED - constants
        if missing:
            failures.append(f"{path}: missing constants: {sorted(missing)}")
        rel = path.relative_to(RULES_DIR)
        test_path = TESTS_DIR / rel.parent / f"test_{rel.name}"
        if not test_path.exists():
            failures.append(f"{path}: no matching test file at {test_path}")
    if failures:
        for f in failures:
            print(f, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
