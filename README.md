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

### Prerequisite: `uv`

`pba` is built and distributed with [uv](https://docs.astral.sh/uv/). If you
don't have it yet:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Homebrew (macOS / Linux)
brew install uv

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your shell (or `source ~/.zshrc` / `~/.bashrc`) and verify:

```bash
uv --version
```

### Install `pba`

```bash
uv tool install git+https://github.com/databricks-solutions/powerbi-analyzer
# or for development
git clone https://github.com/databricks-solutions/powerbi-analyzer.git && cd powerbi-analyzer
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

See `[examples/sample-report.md](examples/sample-report.md)` and
`[examples/sample-report.html](examples/sample-report.html)` for what the report looks like
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

## License

&copy; 2025 Databricks, Inc. All rights reserved. The source in this notebook is provided subject to the Databricks License [[https://databricks.com/db-license-source]](https://databricks.com/db-license-source]). All included or referenced third party libraries are subject to the licenses set forth below.


| library                  | description                                                            | license      | source                                                                                                                                           |
| ------------------------ | ---------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| typer                    | Build CLIs from Python type hints                                      | MIT          | [https://github.com/fastapi/typer](https://github.com/fastapi/typer)                                                                             |
| pydantic                 | Data validation and settings management                                | MIT          | [https://github.com/pydantic/pydantic](https://github.com/pydantic/pydantic)                                                                     |
| jinja2                   | HTML report templating                                                 | BSD-3-Clause | [https://github.com/pallets/jinja](https://github.com/pallets/jinja)                                                                             |
| pyyaml                   | YAML parser for `pba.yaml` config                                      | MIT          | [https://github.com/yaml/pyyaml](https://github.com/yaml/pyyaml)                                                                                 |
| rich                     | Terminal formatting for CLI output                                     | MIT          | [https://github.com/Textualize/rich](https://github.com/Textualize/rich)                                                                         |
| msal                     | Microsoft Authentication Library (Power BI device-code / SP auth)      | MIT          | [https://github.com/AzureAD/microsoft-authentication-library-for-python](https://github.com/AzureAD/microsoft-authentication-library-for-python) |
| requests                 | HTTP client for Power BI REST and XMLA Execute Queries                 | Apache-2.0   | [https://github.com/psf/requests](https://github.com/psf/requests)                                                                               |
| databricks-sdk           | Workspace, warehouse, and system-table access                          | Apache-2.0   | [https://github.com/databricks/databricks-sdk-py](https://github.com/databricks/databricks-sdk-py)                                               |
| databricks-sql-connector | SQL warehouse query execution (with `[pyarrow]` extra for cloud fetch) | Apache-2.0   | [https://github.com/databricks/databricks-sql-python](https://github.com/databricks/databricks-sql-python)                                       |
| pyarrow                  | Columnar transport for cloud-fetch result sets                         | Apache-2.0   | [https://github.com/apache/arrow](https://github.com/apache/arrow)                                                                               |
| pbixray                  | Parse `.pbix` / `.pbip` semantic models                                | MIT          | [https://github.com/Hugoberry/pbixray](https://github.com/Hugoberry/pbixray)                                                                     |


The full Databricks DB License text is in [LICENSE.md](LICENSE.md).

## Support Disclaimer

The content provided here is for **reference and educational purposes only**.
It is not officially supported by Databricks under any Service Level Agreements (SLAs).
All materials are provided **AS IS**, without any guarantees or warranties, and are not intended for production use without proper review and testing.

If you encounter issues while using this content, please open a GitHub Issue in this repository.
Issues will be reviewed as time permits, but there are **no formal SLAs** for support.