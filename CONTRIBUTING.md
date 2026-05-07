# Contributing to powerbi-analyzer

This repository is maintained by Databricks and intended for contributions from Databricks Field Engineers. While the repository is public and meant to help anyone running Power BI on Databricks, external contributions are not currently accepted. Feel free to open an issue with requests or suggestions.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/mathieupelletier-db/powerbi-analyzer.git
   cd powerbi-analyzer
   ```

2. Create a virtual environment and install in editable mode with dev extras:
   ```bash
   uv venv && source .venv/bin/activate
   uv pip install -e ".[dev]"
   pre-commit install
   ```

3. Configure authentication for live runs:
   ```bash
   export DATABRICKS_CONFIG_PROFILE="your-profile"
   # or
   export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
   export DATABRICKS_TOKEN="your-token"

   # Power BI (service principal mode)
   export PBI_TENANT_ID="..."
   export PBI_CLIENT_ID="..."
   export PBI_CLIENT_SECRET="..."
   ```

## Code Standards

- **Python**: target 3.11+, type-annotated, follow PEP 8.
- **Type hints**: include annotations for all public functions; the project runs `mypy --strict`.
- **Documentation**: update `README.md` and `src/powerbi_analyzer/pba.example.yaml` when adding user-visible flags or config keys.
- **Naming**: lowercase with underscores for Python modules, lowercase with hyphens for top-level directories.

## Linting and Formatting

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting. Run these before submitting a PR:

```bash
ruff check src tests
ruff format --check src tests

# Auto-fix where possible
ruff check src tests --fix
ruff format src tests
```

## Type Checking

```bash
mypy src/
```

## Testing

```bash
pytest                                   # full suite
pytest -k pbix                           # filter
pytest --cov --cov-report=term-missing   # with coverage (fails under 80%)
PBA_UPDATE_GOLDENS=1 pytest tests/e2e/   # refresh golden reports after intentional output changes
```

Coverage must stay at or above 80% (`fail_under = 80` in `pyproject.toml`).

## Pull Request Process

1. Create a feature branch from `main` (fork if needed).
2. Make your changes with clear, descriptive commits.
3. Add or update tests for any rule, collector, or reporter change. Each rule must have at least 3 tests covering pass / warn-or-error / not-applicable cases.
4. Run `ruff check`, `ruff format --check`, `mypy src/`, and `pytest` locally before pushing.
5. Open a PR with:
   - A brief description of the change
   - Any relevant context or motivation
   - The output of the new or updated test(s)
6. Address review feedback.

## Adding a New Rule

Rules live under `src/powerbi_analyzer/rules/<phase>/<rule_id>.py` (phases: `data_prep`, `sql_serving`, `integration`, `report_design`).

1. Pick the next free rule ID in the phase (`DP-`, `SS-`, `IN-`, `RD-`).
2. Copy an existing rule in the same phase as a template — each rule module exports an `evaluate(...)` function and metadata (`RULE_ID`, `PHASE`, `SEVERITY`, `TITLE`, `RECOMMENDATION`).
3. Add tests under `tests/rules/<phase>/test_<rule>.py` covering at least 3 outcomes (pass, warn/error, not-applicable).
4. Update the rule count in `README.md` if the totals shift.
5. Refresh the golden e2e report: `PBA_UPDATE_GOLDENS=1 pytest tests/e2e/`.

## Security

- Never commit credentials, tokens, or sensitive data.
- Use synthetic fixtures under `tests/fixtures/` for examples and tests.
- The local `~/.cache/pba/<run_id>/` cache is sanitized of secrets, GUIDs, and connection strings — attach it to bug reports.
- Review changes for potential security issues before submitting.

## License

By submitting a contribution, you agree that your contributions will be licensed under the same terms as the project (see [LICENSE.md](LICENSE.md)).

You certify that:
- You have the right to submit the contribution
- Your contribution does not include confidential or proprietary information
- You grant Databricks the right to use, modify, and distribute your contribution
