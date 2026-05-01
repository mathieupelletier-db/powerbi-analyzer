# powerbi-analyzer (`pba`)

CLI that audits Power BI on Databricks setups against the [Databricks Power BI Best Practices Cheat Sheet](2025-04-power-bi-on-databricks-best-practices-cheat-sheet%20%281%29.pdf).

## Install (dev)

```bash
uv venv
uv pip install -e ".[dev]"
pre-commit install
```

## Usage

```bash
pba pbix path/to/report.pbix
pba databricks --profile DEFAULT --catalog main.gold --warehouse-id <id>
pba workspace --workspace-id <guid>
pba scan --config pba.yaml
```

See `docs/superpowers/specs/2026-05-01-powerbi-analyzer-design.md` for design.
