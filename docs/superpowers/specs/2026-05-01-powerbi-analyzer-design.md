# Power BI Analyzer (`pba`) — Design

**Date:** 2026-05-01
**Status:** Approved (pending final user review)
**Reference:** `2025-04-power-bi-on-databricks-best-practices-cheat-sheet.pdf` (committed at repo root)

## 1. Goal & audience

Build a Python CLI, `pba`, that audits a customer's Power BI + Databricks setup against the best practices in the Databricks "Power BI on Databricks Best Practices Cheat Sheet" (April 2025). The tool produces a Markdown and HTML report that the customer's BI engineering team can read, share, and act on.

**Primary user:** customer BI engineer self-auditing their own setup.
**Primary deliverable:** a single-file report (Markdown by default, HTML on demand) suitable for sharing with their team.

**Coverage commitment for v1:** all four phases of the cheat sheet, all three input modes (~42 rules total). Depth before breadth was rejected so the report tells the whole story on day one.

## 2. Three input modes

The CLI exposes three independently usable modes — each maps to one collector that pulls evidence from one source:

- **Mode A — `.pbix` / `.pbip` static analysis.** No credentials needed. Parses the local artifact.
- **Mode B — Live Power BI workspace.** Connects to a tenant via Power BI REST API + DAX `INFO.*` queries to introspect deployed semantic models and workspace settings.
- **Mode C — Databricks-side audit.** Inspects SQL warehouse configuration, query history, Unity Catalog tables, and table-level metadata for the Databricks workloads that back Power BI.

`pba scan` runs any combination configured in `pba.yaml`. Cross-mode rules (e.g., region-match between Power BI capacity and Databricks workspace) activate when both sides are present.

## 3. Output contract

- **Formats:** Markdown by default. HTML on demand via `--out report.html` or `--formats markdown,html` (or set in `pba.yaml`). HTML is self-contained: inline CSS, no external assets except optional Google Fonts (overridable with `--embed-fonts` for air-gapped use).
- **Severity tiers:** `error` (clear bad practice with quantifiable cost), `warn` (suboptimal, may be intentional), `info` (heads-up), `pass` (rule passed), `n/a` (rule not applicable to this artifact).
- **Per-finding payload:** rule ID, name, phase, severity, status, one-line summary, structured evidence dict, why it matters, how to fix, link to cheat-sheet doc, target identifier.
- **Summary:** overall score (0-100, weighted by severity), per-phase scores, counts by severity, top 5 highest-impact issues. Rendered as the first section in both formats.
- **Determinism:** rules execute in `RULE_ID` order; findings sort by phase then severity then ID. Reports diff cleanly across runs.

## 4. Architecture

Shared semantic-model abstraction with rule-per-file. Three layers:

```
                ┌─────────────────────────────────────┐
                │              CLI (Typer)            │
                │  pba pbix / workspace / databricks  │
                │  pba scan / pba init                │
                └────────────────┬────────────────────┘
                                 │
                          ┌──────▼──────┐
                          │   Engine    │   orchestrates run, scoring, exit code
                          └──────┬──────┘
        ┌──────────────────┬─────┴──────┬───────────────────┐
        │                  │            │                   │
   ┌────▼─────┐    ┌───────▼────┐  ┌────▼──────────┐   ┌────▼────────┐
   │ Pbix     │    │ Workspace  │  │ Databricks    │   │  Reporters  │
   │ Collector│    │ Collector  │  │ Collector     │   │  md / html  │
   └────┬─────┘    └───────┬────┘  └────┬──────────┘   └─────────────┘
        │                  │            │
        ▼                  ▼            ▼
  SemanticModel      SemanticModel  WarehouseState
                  + WorkspaceConfig + CatalogState
                            │
                            ▼
                   ┌────────────────┐
                   │  Rule registry │   42 rule files in 4 phase packages
                   └────────────────┘
```

**Why this shape:** mode A and mode B share ~80% of the rules (semantic-model checks). Both collectors produce the same `SemanticModel` shape so a single rule like `avoid_many_to_many` works against both. Mode C contributes its own state types. Cross-mode rules consume multiple inputs naturally because the engine resolves rule signatures from type hints.

## 5. Project layout

```
powerbi-analyzer/
├── pyproject.toml                 # hatchling build, console script `pba`
├── README.md
├── pba.example.yaml               # committed template; `pba init` copies it to ./pba.yaml in the user's cwd
├── docs/superpowers/specs/
├── examples/                      # sample reports (md + html) generated from fixtures
├── src/powerbi_analyzer/
│   ├── __init__.py
│   ├── cli.py                     # Typer entry point
│   ├── config.py                  # pba.yaml + env var interpolation
│   ├── engine.py                  # collectors -> rules -> findings -> reporters
│   ├── domain/
│   │   ├── finding.py
│   │   ├── semantic_model.py
│   │   ├── warehouse.py
│   │   └── catalog.py
│   ├── collectors/
│   │   ├── base.py
│   │   ├── pbix.py
│   │   ├── workspace.py
│   │   └── databricks.py
│   ├── rules/
│   │   ├── _registry.py
│   │   ├── data_prep/
│   │   ├── sql_serving/
│   │   ├── integration/
│   │   └── report_design/
│   └── reporters/
│       ├── markdown.py
│       └── html.py                # Jinja2 template + inline CSS
└── tests/
    ├── builders.py                # shared Pydantic builders for unit tests
    ├── fixtures/
    │   ├── pbix/                  # sample .pbix and .pbip
    │   ├── workspace/cassettes/   # vcrpy recordings
    │   ├── databricks/            # mocked REST + system-table fixtures
    │   └── scenarios/
    │       ├── small_good/
    │       └── small_bad/
    ├── golden/                    # golden md + html for e2e tests
    ├── rules/                     # one test file per rule
    └── e2e/
```

**Distribution:** `uv tool install .` or `pipx install .`. Python 3.11+.

## 6. CLI surface

```
pba init                                      # writes a starter pba.yaml in cwd
pba pbix <path>...                            # mode A; accepts globs
pba workspace --workspace-id <id> [...]       # mode B
pba databricks --profile <p> --catalog ...    # mode C
pba scan [--config pba.yaml]                  # runs all configured modes, single combined report
```

**Common flags:**

- `--out <path>` — explicit output path (extension chooses format)
- `--out-dir <dir> --formats markdown,html` — emit both, named `pba-audit-{YYYY-MM-DD}-{run_id_short}.{ext}`
- `--severity-threshold {error,warn,info}`
- `--rules <glob>` / `--ignore <rule-id>`
- `--fail-on {none,error,warn}` — exit-code policy (default `none`)
- `--no-color`, `--verbose`, `--quiet`
- `--embed-fonts` — inline DM Sans woff2 in the HTML report (air-gapped)
- `--no-cache` / `--from-cache <run_id>` — bypass / reuse the per-run collector cache

**Config file (`pba.yaml`):**

```yaml
output:
  formats: [markdown, html]
  dir: reports/

pbix:
  files: ["reports/*.pbix"]

workspace:
  tenant_id: ${PBI_TENANT_ID}
  workspace_id: <guid>
  datasets: auto              # or explicit list of dataset GUIDs
  auth: device_code           # device_code | service_principal

databricks:
  profile: DEFAULT
  warehouse_id: <id>
  catalogs: ["main.gold", "main.silver"]
  query_history_lookback_days: 30

rules:
  ignore: ["RD-007"]
```

`${VAR}` env var interpolation throughout. `pba init` writes a commented version of this file with placeholder values and a list of required Power BI scopes / Databricks permissions.

## 7. Domain model (Pydantic v2)

### Finding

```python
class Severity(StrEnum): ERROR; WARN; INFO; PASS; NA
class Status(StrEnum):   FAIL; PASS; SKIPPED; NOT_APPLICABLE
class Phase(StrEnum):    DATA_PREP; SQL_SERVING; INTEGRATION; REPORT_DESIGN

class Finding(BaseModel):
    rule_id: str               # phase-prefixed: DP-###, SS-###, IN-###, RD-###
    rule_name: str
    phase: Phase
    severity: Severity         # rule's declared max severity
    status: Status             # actual outcome for this run
    summary: str               # 1 line
    evidence: dict[str, Any]   # structured; rendered as kv table in HTML
    why: str                   # 1-3 sentences from the cheat sheet
    fix: str                   # actionable guidance
    docs_url: str | None
    target: str                # what was audited
```

**Severity / status invariants:**

- `status == PASS` ⇒ `severity == PASS` (a passing rule does not carry its declared severity).
- `status == FAIL` ⇒ `severity` is the rule's declared `SEVERITY` (rules don't dynamically escalate).
- `status == NOT_APPLICABLE` ⇒ `severity == NA`.
- `status == SKIPPED` (e.g., `--ignore`) ⇒ excluded from scoring; `severity` retains the rule's declared value for display.

### SemanticModel (produced by `PbixCollector` and `WorkspaceCollector`)

```python
class StorageMode(StrEnum): IMPORT; DIRECT_QUERY; DUAL; CALCULATED

class Column(BaseModel):
    name: str
    data_type: str                 # int64, double, string, datetime, decimal, boolean, binary
    cardinality: int | None        # None when source can't tell
    is_nullable: bool
    is_key: bool
    is_hidden: bool
    summarize_by: str | None
    encoding_hint: str | None      # value/hash; workspace mode only

class Partition(BaseModel):
    name: str
    source_type: str               # m, dax, calculated, calculatedTable, entity
    source_expression: str | None
    refresh_policy: RefreshPolicy | None

class Table(BaseModel):
    name: str
    columns: list[Column]
    row_count: int | None
    is_hidden: bool
    storage_mode: StorageMode
    partitions: list[Partition]
    is_aggregation_table: bool
    aggregation_targets: list[str]

class Relationship(BaseModel):
    from_table: str; from_column: str
    to_table: str;   to_column: str
    cardinality: Literal["one-to-one","one-to-many","many-to-many"]
    cross_filter: Literal["single","both","none"]
    is_active: bool
    assume_referential_integrity: bool

class Measure(BaseModel):
    name: str; table: str; expression: str
    format_string: str | None
    referenced_columns: list[str]   # parsed from DAX
    referenced_measures: list[str]

class Visual(BaseModel):
    page: str; visual_type: str
    fields_used: list[str]          # table.column or table.measure
    filters: list[str]

class SemanticModel(BaseModel):
    name: str
    source: Literal["pbix", "pbip", "workspace"]
    tables: list[Table]
    relationships: list[Relationship]
    measures: list[Measure]
    calculated_columns: list[CalculatedColumn]
    calculated_tables: list[CalculatedTable]
    visuals_by_page: dict[str, list[Visual]]
    aggregations: list[Aggregation]
    is_composite: bool
    has_hybrid_tables: bool
    parameters: list[Parameter]
    query_reduction_settings: QueryReductionConfig | None
```

### WorkspaceConfig (mode B only)

```python
class WorkspaceConfig(BaseModel):
    workspace_id: str
    capacity_region: str | None
    sso_enabled: bool
    gateway: GatewayConfig | None
    parallelism: ParallelismConfig            # max connections, simultaneous evals, max parallelism per query
    publish_to_pbi_service: bool
    automatic_publishing: bool
```

### WarehouseState + CatalogState (mode C)

```python
class WarehouseState(BaseModel):
    warehouse_id: str; name: str
    type: Literal["serverless","pro","classic"]
    cluster_size: str                          # 2X-Small … 4X-Large
    auto_stop_mins: int | None
    min_clusters: int; max_clusters: int
    region: str
    query_history: list[QueryHistoryEntry]
    events: list[WarehouseEvent]

class TableMetadata(BaseModel):
    full_name: str                             # catalog.schema.table
    layer: Literal["bronze","silver","gold","unknown"]
    columns: list[ColumnMetadata]
    primary_key: list[str] | None
    foreign_keys: list[ForeignKey]
    rely: bool
    clustering: ClusteringInfo                 # liquid | zorder | partitioned | none
    last_optimize_at: datetime | None
    last_vacuum_at: datetime | None
    predictive_optimization: bool
    has_column_stats: bool
    is_materialized_view: bool

class CatalogState(BaseModel):
    tables: list[TableMetadata]
    referenced_by_powerbi: list[str]           # tables hit by PBI query history
```

**Sub-types referenced above** — `RefreshPolicy`, `CalculatedColumn`, `CalculatedTable`, `Aggregation`, `Parameter`, `QueryReductionConfig`, `GatewayConfig`, `ParallelismConfig`, `QueryHistoryEntry`, `WarehouseEvent`, `ColumnMetadata`, `ForeignKey`, `ClusteringInfo` — are defined alongside their parent in the same module. Each is a small Pydantic model; details (field names, types) belong to the implementation plan, not this spec.

## 8. Collectors

### `PbixCollector` (mode A)

- **Input:** path to `.pbix` file or `.pbip` project folder; supports globs.
- **Library:** [`pbixray`](https://pypi.org/project/pbixray/) (pure-Python) for `.pbix`. `.pbip` is parsed by reading TMDL/JSON files directly — no extra library.
- **Output:** `SemanticModel` with `source = "pbix" | "pbip"`. No `WorkspaceConfig`.
- **Limitations surfaced as `n/a` findings, not crashes:**
  - `.pbix` does not expose live cardinality; cardinality-dependent rules emit `n/a` with "switch to mode B for live cardinality."
  - Encrypted / sensitivity-labeled `.pbix` files: collector emits a single `error`-status finding for that file ("Cannot parse encrypted .pbix") and continues with any other files in the same run. The overall run does not crash.
  - Visual extraction from `.pbix` layout JSON is best-effort; opaque field bindings are flagged in evidence rather than guessed.

### `WorkspaceCollector` (mode B)

- **Input:** `tenant_id`, `workspace_id`, optional `dataset_id` (defaults to all datasets in workspace), auth method.
- **Auth:** `msal` library.
  - **Device code flow** (default for self-audit): user runs the command, browses to `microsoft.com/devicelogin`, authorizes once. Token cache at `~/.cache/pba/msal_cache.json` with `0600` permissions.
  - **Service principal** via `PBI_TENANT_ID`, `PBI_CLIENT_ID`, `PBI_CLIENT_SECRET` env vars or `pba.yaml`.
- **Required Power BI scopes:** `Dataset.Read.All`, `Workspace.Read.All`, `Tenant.Read.All` (capacity region). Listed in the `pba init` README.
- **Two API paths:**
  1. Power BI REST API (`api.powerbi.com/v1.0/myorg/...`) for workspace config, dataset list, parallelism, gateway, capacity region, refresh history.
  2. The "Execute Queries" REST endpoint to run `INFO.*()` DAX functions (`INFO.TABLES`, `INFO.RELATIONSHIPS`, `INFO.MEASURES`, etc.) and `EVALUATE` to introspect the model. **This avoids the ADOMD .NET dependency, which is a non-starter on macOS/Linux.**
- **Output:** `SemanticModel` (with real cardinality from `INFO.TABLES` row counts) plus `WorkspaceConfig`.

### `DatabricksCollector` (mode C)

- **Input:** Databricks profile (or env-var auth chain), `warehouse_id`, list of catalog/schema names to scan, query history lookback days.
- **Library:** `databricks-sdk` (auth + Workspace REST) and `databricks-sql-connector` for system-table queries.
- **Two data paths:**
  1. Workspace REST: `GET /api/2.0/sql/warehouses/{id}` for warehouse type, size, auto-stop, scaling, region.
  2. SQL warehouse queries against:
     - `system.query.history` filtered to `warehouse_id` and `client_application LIKE '%Power BI%'`
     - `system.compute.warehouse_events`
     - `system.information_schema.tables` / `column_statistics` / `table_constraints` / `key_column_usage`
     - `DESCRIBE EXTENDED` and `DESCRIBE DETAIL` per table for clustering, partitioning, last optimize/vacuum (not yet fully in info_schema).
- **Permissions validated upfront** (fail fast with clear message): `USE CATALOG` on each scanned catalog; `SELECT` on the listed `system.*` tables; `CAN_USE` on the warehouse.
- **Output:** `WarehouseState` + `CatalogState`.

### Cross-cutting

- **Caching:** every collector writes raw output to `~/.cache/pba/{run_id}/` as JSON. `--no-cache` / `--from-cache <run_id>` for dev-loop speedups.
- **Errors:** auth failures, missing permissions, and unreachable endpoints emit a structured `CollectorError` shown as a banner in the report. Other modes continue.
- **Redaction:** the cache and any debug-level logs run through a redactor that masks dataset GUIDs, table values, and connection strings before disk write — the user will share the report with their team.

## 9. Rule contract & engine

### Rule file shape

```python
# rules/report_design/avoid_many_to_many.py
from powerbi_analyzer.rules import rule, Finding, Severity, Status

RULE_ID = "RD-005"
NAME = "Avoid many-to-many relationships"
PHASE = "report_design"
SEVERITY = Severity.WARN
APPLIES_TO = ["pbix", "workspace"]
DOCS_URL = "https://learn.microsoft.com/.../many-to-many"

@rule(RULE_ID)
def check(model: SemanticModel) -> Finding:
    m2m = [r for r in model.relationships if r.cardinality == "many-to-many"]
    if not m2m:
        return Finding.passed(RULE_ID, NAME, summary="No many-to-many relationships found.")
    return Finding.failed(
        RULE_ID, NAME,
        severity=Severity.WARN,
        summary=f"{len(m2m)} many-to-many relationship(s) detected.",
        evidence={"relationships": [f"{r.from_table}↔{r.to_table}" for r in m2m]},
        why="Many-to-many relationships add bridge-table complexity and can degrade query plans.",
        fix="Replace with a bridge dimension or denormalize at the gold layer.",
    )
```

**Conventions enforced by the registry on import:**

- Required module constants: `RULE_ID`, `NAME`, `PHASE`, `SEVERITY`, `APPLIES_TO`, `DOCS_URL`. Missing constant → registry refuses to load and surfaces a clean error.
- `RULE_ID` unique across all rules and prefix-matches its phase: `DP-###`, `SS-###`, `IN-###`, `RD-###`.
- `check`'s parameters are resolved by **type hints** against the engine's context dict. A rule needing both `SemanticModel` and `WarehouseState` declares both; the engine wires them up automatically.

### Discovery

`_registry.py` does a one-time `pkgutil.walk_packages` of the `rules/` sub-packages, validates each module, and adds it to a `RuleSet`. No setuptools entry-points — files in folders.

A rule can be excluded via `--ignore RD-005`, `rules.ignore: ["RD-005"]` in `pba.yaml`, or a `# pba: skip` comment at the top of the rule file.

### Engine flow

```
1. Parse CLI / config -> list of (Mode, target) tuples
2. For each mode, instantiate the matching collector and call .collect() -> typed output
   (SemanticModel | (SemanticModel + WorkspaceConfig) | (WarehouseState + CatalogState))
3. Merge collector outputs into a single context dict, keyed by type
4. For each rule in RuleSet:
     a. Skip with NOT_APPLICABLE if APPLIES_TO ∩ active_modes is empty
     b. Resolve check() parameter type hints against the context dict
     c. Run inside try/except; convert exceptions to ERROR finding "Rule crashed: <msg>"
5. Aggregate Findings -> per-phase scores + overall score
6. Emit through each configured Reporter
7. Compute exit code per --fail-on policy
```

### Score model

- Each rule has phase weight (1× in v1) and severity weight (`error=3, warn=2, info=1`).
- Per-phase score = `100 × (max_score − sum(weight × failed)) / max_score`, clipped at 0.
- Overall score = average of the four phase scores.
- Phase weights uniform in v1; tunable later from real-world report data.

### Performance budget

For 1 `.pbix` + 1 workspace with 20 datasets + 1 warehouse with 100 tables:

- Mode A: ~2–5 sec per file (dominated by `pbixray` parse).
- Mode B: ~30–60 sec for token + 20 datasets via REST + DAX `INFO.*` calls.
- Mode C: ~10–30 sec; system-table queries batched into a handful of multi-statement requests.

Target: full `pba scan` under two minutes. Per-dataset / per-table parallelism deferred to a future version if needed.

## 10. Rule inventory (42 rules)

### Data Preparation (mode C only)

| ID | Rule | Sev | What we check |
|---|---|---|---|
| DP-001 | Adopt medallion architecture | warn | Heuristic: tables hit by PBI query history outside `gold` / `serving` / `mart` schemas. |
| DP-002 | Use star schema | info | Detect snowflake patterns: dimension tables joining to other dimensions. Best-effort. |
| DP-003 | SQL views / persisted tables for granularity | info | Flag PBI queries repeatedly aggregating very large fact scans. |
| DP-004 | Declare PK / FK with RELY | error | For tables hit by PBI: missing PK constraint, or constraint without `RELY`. |
| DP-005 | Avoid wide / high-cardinality types | warn | `STRING` columns with `MAX_LEN_OBSERVED > 1000`; any `BINARY` / `STRUCT` referenced by PBI. |
| DP-006 | Use auto-generated (computed) columns | info | Detect repeated DAX expressions that could be precomputed in Delta. Heuristic from query history. |
| DP-007 | Use Liquid Clustering (or Z-order) | warn | Tables > 10 GB hit by PBI without Liquid Clustering or Z-order. Threshold configurable. |
| DP-008 | Predictive Optimization or recent OPTIMIZE/VACUUM | warn | PO disabled AND last `OPTIMIZE` > 30 days OR last `VACUUM` > 30 days. |
| DP-009 | Compute statistics | info | Tables hit by PBI without `ANALYZE TABLE` stats and not enrolled in automatic stats. |
| DP-010 | Evaluate materialized views | info | Identify expensive repeated aggregations as MV candidates. |

### SQL Serving (mode C only)

| ID | Rule | Sev | What we check |
|---|---|---|---|
| SS-001 | Use SQL warehouse, not all-purpose cluster | error | Query history: PBI queries on an all-purpose cluster instead of a SQL warehouse. |
| SS-002 | Use Serverless | warn | Warehouse type ≠ `serverless`. |
| SS-003 | Enable Auto stop | warn | `auto_stop_mins` is null or > 60. |
| SS-004 | Right-size for dataset | info | Warehouse size cross-referenced with avg query memory from `query_history.compute_used`. Flags too-small only. |
| SS-005 | Configure scaling (min/max clusters) | warn | `max_clusters == 1` AND query history shows queueing. |
| SS-006 | Increase min clusters if many concurrent queries | warn | Queries waiting > 5 sec AND `min_clusters == 1`. |
| SS-007 | Same warehouse for same dataset | info | Same dataset hit from multiple warehouses → cache fragmentation. |
| SS-008 | Separate warehouses for different workloads | info | Single warehouse handling both BI and ETL traffic (heuristic from `client_application`). |
| SS-009 | Reasonable starting size if unset | info | Warehouse at `2X-Small` and either queueing or spilling. |
| SS-010 | Monitor via system tables | info | `system.compute.warehouse_events` shows scaling-out events but no min/max change recently. |

### PBI Integration

| ID | Rule | Sev | What we check | Modes |
|---|---|---|---|---|
| IN-001 | Same region for PBI and Databricks | warn | `WorkspaceConfig.capacity_region` ≠ `WarehouseState.region`. Falls back to info if only one mode ran. | B + C |
| IN-002 | DirectQuery for Fact, Dual for Dimensions | warn | Heuristic: tables named `*fact*` or large rowcount in Import; small `*dim*` tables not in Dual. | A, B |
| IN-003 | Composite models considered | info | All tables one storage mode → flag as candidate. | A, B |
| IN-004 | Hybrid tables for hot+cold | info | Large fact in pure DirectQuery with no aggregation table → candidate. | A, B |
| IN-005 | Incremental refresh for Import tables | warn | Import-mode tables > 1M rows without `RefreshPolicy`. | A, B |
| IN-006 | Query parallelization tuned | warn | `MaxParallelismPerQuery` at default AND PBI workload visible in query history. | B (+ C for evidence) |
| IN-007 | SSO enabled | error | `WorkspaceConfig.sso_enabled == False`. | B |
| IN-008 | Use parameters for environment switching | info | Connection string is a hardcoded SQL warehouse URL, not parameterized. | A, B |
| IN-009 | Gateway clusters configured | info | If a gateway is configured, ensure cluster mode (multiple gateways), not single-node. | B |
| IN-010 | Use Publish to PBI Service from Databricks | info | If catalog has online_to_powerbi integration available, recommend it. | B + C |
| IN-011 | Automatic Publishing from UC | info | UC Gold-schema tables not enrolled in Automatic Publishing. | B + C |

### PBI Report Design (modes A, B)

| ID | Rule | Sev | What we check |
|---|---|---|---|
| RD-001 | Limit visuals per page | warn | Page with > 12 visuals (configurable). |
| RD-002 | Limit rows/columns surfaced | warn | DirectQuery table with > 50 columns referenced; visual `TopN` over wide column set. |
| RD-003 | User-defined aggregations | info | Large DirectQuery facts (> 100M rows expected) without aggregation table mapped. |
| RD-004 | Automatic aggregations | info | DirectQuery model without `automaticAggregations` enabled. |
| RD-005 | Avoid many-to-many | warn | Any `many-to-many` relationship in the model. |
| RD-006 | Assume Referential Integrity | warn | One-to-many fact↔dim where fact column is NOT NULL but `assumeReferentialIntegrity == false`. |
| RD-007 | Configure "Is nullable" | info | Columns marked nullable that are NOT NULL in the source. Cross-mode: needs C to confirm source nullability. |
| RD-008 | Move-left transformations | warn | M code containing transformations (`Table.AddColumn`, `Table.Group`, joins) that could be SQL views. AST scan. |
| RD-009 | Efficient DAX | warn | Heuristic DAX scan: nested `FILTER`s, repeated `CALCULATE`, `SUMX(table, column)` (vs `SUM`). Best-effort. |
| RD-010 | Query reduction settings | info | Page-level "Apply All Slicers" button absent on pages with > 3 slicers. |
| RD-011 | Avoid DAX calculated columns / tables | warn | Count and list each calculated column / calculated table; severity scales with host-table cardinality. |

**Total: 42 rules.**

- **31 deterministic** (state X exists or not, no judgment).
- **11 heuristic** (DP-001, DP-002, DP-003, DP-006, IN-002, IN-003, IN-004, IN-008, RD-002, RD-008, RD-009): emitted with explicit "best-effort — review and ignore if intentional" wording in the `why` field.

### Implementation order suggestion

Not a commitment, just a starting hint for the implementation plan:

1. The 6 deterministic rules with cleanest payoff: SS-001, SS-002, SS-003, IN-007, RD-005, RD-011. Proves the engine end-to-end across all three modes.
2. The rest of mode C deterministic rules (DP-004, DP-005, DP-007, DP-008, SS-005, SS-006, etc.).
3. Mode A `.pbix` rules (most of RD-*).
4. Mode B workspace rules (most of IN-*).
5. Heuristic rules last — they need real `.pbix` and real query history to validate.

## 11. Reporters

### Markdown

Single `.md` file. Renders cleanly in GitHub, GitLab, VS Code, Cursor, and any Markdown-to-PDF tool.

Top-level structure:

```
# Power BI on Databricks Audit — <target description>
Generated 2026-05-01 14:22 UTC by pba 0.1.0
Modes run: pbix (3 files), workspace, databricks

## Summary
<scores table>
<top 5 issues>

## Data Preparation
### ❌ DP-001 Adopt medallion architecture (error)
<target / observed / why / fix / docs link>
<details><summary>Evidence</summary><fenced JSON></details>
...

## SQL Serving
...
## PBI Integration
...
## PBI Report Design
...
```

Findings grouped by phase, then by severity (error → warn → info → pass → n/a). `--severity-threshold` collapses lower tiers into a single roll-up line. Evidence dicts render as fenced JSON inside `<details>` so the doc reads cleanly but power users can drill in.

### HTML

Single `.html` file, no external assets, no JS framework. Jinja2 template + small inline CSS (~3 KB) + tiny vanilla-JS snippet (~1 KB) for collapse / filter.

Adds over Markdown:

- **Filter bar:** chips for severity and phase. Click to toggle visibility client-side.
- **Sticky summary card** with four phase scores as horizontal bars (CSS only, no chart library).
- **Collapsible evidence** rendered as proper HTML tables instead of JSON code blocks.
- **Click-to-copy** for fix snippets where the rule provides a concrete code suggestion.
- **Print-friendly:** `@media print` block hides the filter bar and expands all collapsed sections so the doc prints to PDF cleanly.

**Branding:** Databricks color palette and DM Sans font (Google Fonts CDN online, system-font fallback offline). `--brand databricks|neutral` for non-Databricks-branded output. `--embed-fonts` inlines the woff2 (~30 KB) for air-gapped use.

**Out of scope for v1:** interactive charts, multi-page output, diff-against-previous-run.

### Output naming

When `--out-dir` is used: `pba-audit-{YYYY-MM-DD}-{run_id_short}.{md,html}`. The `run_id_short` is a 6-char suffix so re-running on the same day doesn't clobber. Explicit `--out path/to/file.html` overrides this.

## 12. Testing strategy

**Layer 1 — Rule unit tests (the bulk).** One test file per rule. Tests construct domain objects directly (Pydantic), call `rule.check(...)`, and assert on the resulting `Finding`. Shared `tests/builders.py` provides `make_model(...)`, `make_warehouse(...)`, etc. with sensible defaults. Target: ≥ 3 tests per rule (pass, fail, edge / `n/a`).

**Layer 2 — Collector integration tests (recorded fixtures).**

- `PbixCollector`: real `.pbix` and `.pbip` files in `tests/fixtures/pbix/`, with `README.md` documenting what each exercises. One "good" model and one "bad" model.
- `WorkspaceCollector`: `vcrpy` cassettes recorded against a development tenant, with `before_record` hook that scrubs tokens, GUIDs, and table values.
- `DatabricksCollector`: `vcrpy` for SDK REST calls; for SQL system-table queries, parameterize the executor so tests inject a stub returning fixture rows from `tests/fixtures/databricks/system_tables/<query_name>.json`.

`pytest --record-cassettes` to refresh against live APIs.

**Layer 3 — End-to-end golden tests.** Full pipeline (`engine.run()` → reporter → diff). Cases: `e2e_pbix_only`, `e2e_workspace_only`, `e2e_databricks_only`, `e2e_scan_all`. HTML golden uses a normalized form (whitespace stripped, run-id replaced) so diffs are stable. `pytest --update-goldens` regenerates.

**Test infra & CI:**

- `pytest`, `pytest-xdist`, `pytest-cov`. ≥ 90% line coverage on `src/powerbi_analyzer/rules/`, ≥ 80% overall.
- `mypy --strict` over the whole codebase — engine relies on type hints for signature resolution, so strict typing is load-bearing.
- `ruff` for lint + format.
- Pre-commit hooks: `ruff`, `mypy`, plus a custom check that every rule file declares the required constants and has a corresponding test file.
- GitHub Actions matrix: Python 3.11 / 3.12 / 3.13 × macOS / Linux / Windows. `.pbix` parsing is the most likely OS-portability hazard.

**Sample data:**

- `tests/fixtures/scenarios/small_good/` — tiny `.pbix` (~10 KB), star schema, all best practices followed. Smoke test + happy-path demo.
- `tests/fixtures/scenarios/small_bad/` — same shape but deliberately violates ~15 rules. Failure-path coverage and source for `examples/sample-report.{md,html}`.

## 13. Out of scope for v1

Tracked here so the implementation plan doesn't drift:

- Interactive charts in HTML report.
- Multi-page HTML output.
- Diff-against-previous-run (would require persisted run state).
- Auto-fix / auto-remediation (the report tells the user what to fix; it doesn't apply fixes).
- Tabular Editor `.bim` ingestion (could be a third collector later; same `SemanticModel` target shape makes this cheap to add).
- Microsoft Fabric semantic-link ingestion.
- `pba serve` web UI (the HTML file is enough for v1).
- Per-dataset / per-table parallelism inside collectors.
- CI-first ergonomics: SARIF / JUnit XML output, GitHub Actions composite action. The CLI's `--fail-on` exit codes and JSON sidecar (in `~/.cache/pba/{run_id}/findings.json`) are sufficient for ad-hoc CI use; first-class CI surfaces wait until v2.

## 14. Open decisions deliberately deferred

- **Phase weighting in score model.** Uniform weights in v1; revisit once we've run on real customer data.
- **Heuristic thresholds** (e.g., "table > 10 GB" for DP-007, "page > 12 visuals" for RD-001). All exposed as config in `pba.yaml` under `thresholds:`; v1 ships with documented defaults.
- **Future SARIF / JUnit output adapters.** Adding another reporter is mechanical; defer until a CI use case is real.
