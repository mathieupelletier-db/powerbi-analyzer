# Auditing Power BI on Databricks Without the Manual Walkthrough

Power BI on top of Databricks SQL is a great combination — and it comes with a long list of small choices that add up. Storage mode on each table. Whether the warehouse is Serverless. Whether SSO actually flows through to Unity Catalog. Whether the report page is hiding 27 visuals behind a slicer. Most of these are documented in the Databricks *Power BI on Databricks Best Practices* cheat sheet, but in practice we end up reviewing them by hand on a call or quietly skipping them. We built `pba` (powerbi-analyzer) to stop doing that.

## The pain: 42 best practices, no audit trail

The April 2025 cheat sheet groups guidance into four phases — Data Preparation, SQL Serving, Power BI Integration, and Power BI Report Design — with a dozen or so checks each. Some are config you can read off a screen ("is the warehouse Serverless?"), some require digging into a `.pbix` ("what storage mode is this fact table?"), some need system tables ("is BI sharing the warehouse with ETL?"), and a few span all three.

Manual review has the usual problems: it's only as good as the reviewer's memory of the cheat sheet, the findings live in a Slack thread nobody opens again, and there's no offline snapshot of what the deployment looked like when something breaks later.

`pba` is a single CLI that turns the cheat sheet into 42 executable rules and produces a single shareable report.

## Three angles, one tool

A Power BI on Databricks deployment has three sides we care about, and `pba` audits all three:

- **The static report files** — `.pbix` or `.pbip` — without any credentials. Useful for PR review, customer artefacts, and pre-deploy checks.
- **The live Power BI workspace** — datasets, refresh policies, gateway / SSO config — through the Power BI REST APIs.
- **The Databricks side** — Unity Catalog tables, clustering, query history, and the warehouse config — through `system.*` tables and the Databricks SDK.

Each side maps to a CLI command (`pba pbix`, `pba workspace`, `pba databricks`) and a single `pba scan` runs whichever ones we have credentials for, from a config file.

## The four phases, with examples

We won't enumerate all 42 rules — the catalog lives in the repo — but here's a representative slice across the phases.

### Data Preparation (Databricks side)

This phase looks at the lakehouse layout that Power BI is reading from.

- **DP-001 — Adopt medallion architecture (serve Gold).** We cross-reference `system.access.table_lineage` with the catalog and flag any Power BI dataset reading from Bronze or Silver. The fix is usually "point Power BI at a `gold` or `mart` schema."
- **DP-007 — Use Liquid Clustering or Z-order on large tables.** Table sizes come from `system.information_schema.tables`, clustering from the table properties. Anything bigger than 10 GB without clustering shows up as a warning, with `ALTER TABLE … CLUSTER BY (…)` in the fix field.

### SQL Serving (Databricks side)

This phase audits the warehouse itself and how it's being used.

- **SS-002 — Use a Serverless SQL warehouse.** A boolean check against the warehouse type, but a high-leverage one: Serverless gives instant elasticity and a shared result cache that survives restarts.
- **SS-008 — Separate warehouses for different workloads.** We bucket query history by client application and flag any warehouse that's serving both BI clients (Power BI, Tableau) and ETL clients (Airflow, dbt jobs). Mixing them is the classic cause of "BI was slow this morning" tickets that line up exactly with an ETL window.

### Power BI Integration (`.pbix`, workspace, Databricks)

This is the connector layer — storage modes, refresh strategy, and how identities flow through.

- **IN-002 — DirectQuery on facts, Dual on dimensions.** We classify each table as fact or dimension by name and row count, then check `StorageMode` from the model. Large facts in Import mode and small dims still in Import (instead of Dual) both surface here. This is the rule that catches "we imported 80M rows of orders and now refresh takes 90 minutes."
- **IN-005 — Incremental refresh for large Import tables.** Any Import-mode table over 1M rows without a `RefreshPolicy` gets flagged.
- **IN-007 — Enable SSO between Power BI and Databricks.** An ERROR-severity rule, because without SSO, the Unity Catalog access controls we just spent two sprints setting up don't actually flow through to report viewers.

### Power BI Report Design (`.pbix`, workspace)

The report-side checks that don't need any infrastructure to run.

- **RD-001 — Limit visuals per page.** Pages with more than 12 visuals get flagged. Each visual fires its own DAX query, so a 30-visual landing page is 30 round-trips on every filter change.
- **RD-011 — Avoid DAX calculated columns and tables.** We list every calculated column and every calculated table the model contains, with the suggestion to push them down into the Gold layer.

Each finding includes a short *why*, a concrete *fix*, and a docs link, so the report is useful to someone who wasn't on the audit call.

## Running it

The three commands cover the three angles directly. The static `.pbix` audit needs no credentials, so start there:

```bash
pba pbix reports/sales-dashboard.pbix --out reports/audit.md
pba pbix reports/sales-dashboard.pbip --out reports/audit.html
```

For the live workspace, device-code auth is fine for an interactive run; service-principal is what we use in CI.

```bash
pba workspace \
  --workspace-id 8b3a... \
  --tenant-id    9f1c... \
  --auth         device_code
```

For Databricks, point at a profile from `~/.databrickscfg`, a warehouse, and one or more catalogs.

```bash
pba databricks \
  --profile DEFAULT \
  --warehouse-id 0123abcd \
  --catalog main.gold \
  --lookback-days 30
```

For end-to-end audits, `pba init` writes a starter `pba.yaml` and `pba scan` runs whichever modes have credentials configured.

```yaml
output:
  formats: [markdown, html]
  dir: reports/

pbix:
  files: ["reports/*.pbix"]

workspace:
  tenant_id: ${PBI_TENANT_ID}
  workspace_id: <guid>
  datasets: auto
  auth: device_code

databricks:
  profile: DEFAULT
  warehouse_id: <id>
  catalogs: ["main.gold"]
  query_history_lookback_days: 30

rules:
  ignore: []   # e.g., ["RD-007"]
```

```bash
pba init
pba scan
```

Both per-command and `pba scan` runs return non-zero exit codes when `--fail-on warn` or `--fail-on error` is set, so it slots into CI without fuss.

## Output you can actually share

Two renderers ship in the box. The **Markdown** report is what we drop into PRs, Confluence pages, and customer run-books — a phase-by-phase score table plus one section per finding with the `why` / `fix` / docs link. The **HTML** report is a single self-contained file (embedded CSS, JS, and the DM Sans font, no external assets), safe to email, drop on a SharePoint, or attach to a Jira ticket.

Pick the format inline:

```bash
pba pbix reports/sales.pbix --out reports/audit.html      # inferred from .html
pba databricks --warehouse-id 0123abcd --catalog main.gold --out reports/audit.html
```

Or write both side-by-side from `pba.yaml`:

```yaml
output:
  formats: [markdown, html]
  dir: reports/
```

## Safe to attach to bug reports

Every run also writes a snapshot of the collected data to `~/.cache/pba/<run_id>/` — the table catalog, the warehouse config, the semantic model, and the query history sample. Before anything is written, we run it through a redactor that strips GUIDs, passwords, tokens, and connection-string secrets. That means when a rule misfires or a check looks wrong on your deployment, attaching the cache directory to a GitHub issue is enough for us to reproduce locally without leaking workspace identifiers or credentials.

## What's next

Run it on one of your own deployments. The fastest path is `uv tool install git+https://github.com/mathieupelletier-db/powerbi-analyzer`, then `pba pbix` against any report you have lying around — no auth, no setup. From there, `pba init` and `pba scan` to layer in the workspace and Databricks sides.

Where we'd love help: new rules (each one is a single file under `src/powerbi_analyzer/rules/<phase>/`, usually under 50 lines), tighter heuristics on the best-effort checks (fact-vs-dimension naming, large-table thresholds), and real-world feedback when a rule fires on a deployment where you intentionally chose the "violating" path. Open an issue with the redacted cache and we'll add an exception or relax the heuristic.

The cheat sheet is a great document. Running it as code is better.
