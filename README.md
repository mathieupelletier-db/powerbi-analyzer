# powerbi-analyzer (`pba`)

Audit a Power BI on Databricks setup against the Databricks
[Power BI on Databricks Best Practices Cheat Sheet](2025-04-power-bi-on-databricks-best-practices-cheat-sheet.pdf).
Produces a single Markdown or HTML report you can share with your team.

## What it checks

42 rules across four phases:


| Phase                  | Modes                          | Rules           |
| ---------------------- | ------------------------------ | --------------- |
| Data Preparation       | Databricks side                | DP-001 … DP-010 |
| SQL Serving            | Databricks side                | SS-001 … SS-010 |
| Power BI Integration   | `.pbix`, workspace, Databricks | IN-001 … IN-011 |
| Power BI Report Design | `.pbix`, workspace             | RD-001 … RD-011 |


See `docs/superpowers/specs/2026-05-01-powerbi-analyzer-design.md` for the full rule catalog.

## Install

```bash
uv tool install git+https://github.com/mathieupelletier-db/powerbi-analyzer
# or for development
git clone … && cd powerbi-analyzer
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
```

## Usage

### Static `.pbix` analysis (no credentials)

```bash
pba pbix path/to/report.pbix --out reports/audit.md
pba pbix path/to/report.pbip --out reports/audit.html
```

### Live Power BI workspace

```bash
pba workspace --workspace-id <guid> --tenant-id <guid> --auth device_code
# follow the device-code prompt in your browser
```

Required Power BI scopes: `Dataset.Read.All`, `Workspace.Read.All`, `Tenant.Read.All`.

For unattended use, set `PBI_TENANT_ID`, `PBI_CLIENT_ID`, `PBI_CLIENT_SECRET` and pass `--auth service_principal`.

### Databricks-side audit

```bash
pba databricks --profile DEFAULT --warehouse-id <id> --catalog main.gold
```

Required permissions:

- `USE CATALOG` on each scanned catalog
- `SELECT` on `system.query.history`, `system.compute.warehouse_events`, `system.information_schema.*`
- `CAN_USE` on the warehouse

### Scan everything from a config file

```bash
pba init                 # writes pba.yaml
$EDITOR pba.yaml         # fill in credentials and targets
pba scan                 # produces a single combined report
```

## Output formats

Two renderers are supported: `markdown` (default) and `html` (single self-contained
file with embedded CSS, JS, and DM Sans font — safe to email or drop on a share).

Per-command (`pba pbix`, `pba workspace`, `pba databricks`):

```bash
pba pbix report.pbix --out reports/audit.html        # inferred from .html suffix
pba pbix report.pbix --out reports/audit.md --formats html   # or forced via flag
```

From `pba.yaml` (used by `pba scan`):

```yaml
output:
  formats: [markdown, html]   # any subset; both written side-by-side
  dir: reports/
```

## Sample output

See [`examples/sample-report.md`](examples/sample-report.md) and
[`examples/sample-report.html`](examples/sample-report.html) for what the report looks like
on the deliberately-bad fixture.

## Development

```bash
pytest                   # run all tests
mypy src/                # type-check
ruff check src tests     # lint
ruff format src tests    # format
PBA_UPDATE_GOLDENS=1 pytest tests/e2e/  # refresh golden reports
```

## Reporting issues

Please attach the contents of `~/.cache/pba/<run_id>/` (collector outputs, redacted) when filing
a bug — the cache is sanitized of secrets, GUIDs, and connection strings.