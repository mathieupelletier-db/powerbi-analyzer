# Power BI on Databricks Audit — small_bad.pbip

Generated 2026-05-01 16:54 UTC by pba 0.1.0

Modes run: pbix

## Summary

| Phase | Score | Pass | Warn | Error | Info | N/A |
|---|---|---|---|---|---|---|
| Data Preparation | — | — | — | — | — | — |
| SQL Serving | — | — | — | — | — | — |
| Power BI Integration | 33/100 | 2 | 1 | 0 | 2 | 6 |
| Power BI Report Design | 54/100 | 7 | 3 | 0 | 0 | 1 |
| **Overall** | **44/100** | | | | | |

### Top 5 highest-impact issues

1. **[IN-002] Use DirectQuery on facts and Dual on dimensions** (warn) — 1 fact(s) in Import, 2 dim(s) not in Dual.
2. **[RD-005] Avoid many-to-many relationships** (warn) — 1 many-to-many relationship(s) detected.
3. **[RD-006] Use Assume Referential Integrity where valid** (warn) — 1 relationship(s) eligible for Assume Referential Integrity.
4. **[RD-011] Avoid DAX calculated columns and calculated tables** (warn) — 1 calculated column(s); 0 calculated table(s).
5. **[IN-003] Consider composite models** (info) — All 3 tables use the same storage mode.

## Data Preparation

### — DP-001 Adopt medallion architecture (serve Gold) (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/lakehouse/medallion.html](https://docs.databricks.com/lakehouse/medallion.html)

### — DP-002 Use star schema (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://learn.microsoft.com/power-bi/guidance/star-schema](https://learn.microsoft.com/power-bi/guidance/star-schema)

### — DP-003 Use SQL views or persisted tables for repeated aggregations (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/user/queries/index.html](https://docs.databricks.com/sql/user/queries/index.html)

### — DP-004 Declare PK/FK with RELY (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/tables/constraints.html](https://docs.databricks.com/tables/constraints.html)

### — DP-005 Avoid wide and high-cardinality types (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/tables/index.html](https://docs.databricks.com/tables/index.html)

### — DP-006 Use auto-generated (computed) columns (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/language-manual/sql-ref-syntax-ddl-create-table-using.html](https://docs.databricks.com/sql/language-manual/sql-ref-syntax-ddl-create-table-using.html)

### — DP-007 Use Liquid Clustering or Z-order (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/delta/clustering.html](https://docs.databricks.com/delta/clustering.html)

### — DP-008 Predictive Optimization or recent OPTIMIZE/VACUUM (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/optimizations/predictive-optimization.html](https://docs.databricks.com/optimizations/predictive-optimization.html)

### — DP-009 Compute column statistics (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/language-manual/sql-ref-syntax-aux-analyze-table.html](https://docs.databricks.com/sql/language-manual/sql-ref-syntax-aux-analyze-table.html)

### — DP-010 Evaluate materialized views (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/user/materialized-views.html](https://docs.databricks.com/sql/user/materialized-views.html)

## SQL Serving

### — SS-001 Use SQL warehouse, not all-purpose cluster (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html](https://docs.databricks.com/sql/admin/sql-endpoints.html)

### — SS-002 Use Serverless SQL warehouse (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/admin/serverless.html](https://docs.databricks.com/sql/admin/serverless.html)

### — SS-003 Enable SQL warehouse Auto stop (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#auto-stop](https://docs.databricks.com/sql/admin/sql-endpoints.html#auto-stop)

### — SS-004 Right-size warehouse for dataset (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#sizes](https://docs.databricks.com/sql/admin/sql-endpoints.html#sizes)

### — SS-005 Configure SQL warehouse scaling (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#scaling](https://docs.databricks.com/sql/admin/sql-endpoints.html#scaling)

### — SS-006 Increase min clusters for concurrent traffic (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#scaling](https://docs.databricks.com/sql/admin/sql-endpoints.html#scaling)

### — SS-007 Same warehouse for same dataset (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#cache](https://docs.databricks.com/sql/admin/sql-endpoints.html#cache)

### — SS-008 Separate warehouses for different workloads (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html](https://docs.databricks.com/sql/admin/sql-endpoints.html)

### — SS-009 Reasonable starting warehouse size (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/sql/admin/sql-endpoints.html#sizes](https://docs.databricks.com/sql/admin/sql-endpoints.html#sizes)

### — SS-010 Monitor via system tables (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/admin/system-tables/index.html](https://docs.databricks.com/admin/system-tables/index.html)

## Power BI Integration

### ⚠️ IN-002 Use DirectQuery on facts and Dual on dimensions (warn)
**Target:** small_bad
**Status:** fail
**Summary:** 1 fact(s) in Import, 2 dim(s) not in Dual.
**Why it matters:** Import-mode facts can outgrow capacity; Dual dims allow dim filters to fold into either path.
**How to fix:** Set fact tables to DirectQuery, small dimensions to Dual.
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-storage-mode](https://learn.microsoft.com/power-bi/transform-model/desktop-storage-mode)
                <details><summary>Evidence</summary>

                ```json
                {
  "facts_in_import": [
    "Fact_Sales"
  ],
  "dims_not_dual": [
    "Dim_Customer",
    "Dim_Region"
  ],
  "heuristic": "best-effort — review and ignore if intentional"
}
                ```
                </details>

### ℹ️ IN-003 Consider composite models (info)
**Target:** small_bad
**Status:** fail
**Summary:** All 3 tables use the same storage mode.
**Why it matters:** A composite model lets you mix Import (small dims) and DirectQuery (large facts) for both freshness and speed.
**How to fix:** Convert dimensions to Dual or facts to DirectQuery as appropriate.
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-composite-models](https://learn.microsoft.com/power-bi/transform-model/desktop-composite-models)
                <details><summary>Evidence</summary>

                ```json
                {
  "storage_mode": "import",
  "table_count": 3,
  "heuristic": "best-effort — review and ignore if intentional"
}
                ```
                </details>

### ℹ️ IN-008 Use parameters for environment switching (info)
**Target:** small_bad
**Status:** fail
**Summary:** No parameter found for switching connection endpoints.
**Why it matters:** Hardcoded warehouse URLs make dev → prod migration painful.
**How to fix:** Define an M parameter (e.g., 'warehouse_endpoint') and reference it in the connection string.
**Reference:** [https://learn.microsoft.com/power-bi/connect-data/desktop-dynamic-m-query-parameters](https://learn.microsoft.com/power-bi/connect-data/desktop-dynamic-m-query-parameters)
                <details><summary>Evidence</summary>

                ```json
                {
  "parameters": [],
  "heuristic": "best-effort — review and ignore if intentional"
}
                ```
                </details>

### ✅ IN-004 Consider hybrid tables for large facts (pass)
**Target:** small_bad
**Status:** pass
**Summary:** No large pure-DirectQuery facts found.
**Reference:** [https://learn.microsoft.com/power-bi/connect-data/desktop-incremental-refresh#hybrid-tables](https://learn.microsoft.com/power-bi/connect-data/desktop-incremental-refresh#hybrid-tables)

### ✅ IN-005 Use incremental refresh for large Import tables (pass)
**Target:** small_bad
**Status:** pass
**Summary:** All large Import tables use incremental refresh.
**Reference:** [https://learn.microsoft.com/power-bi/connect-data/incremental-refresh-overview](https://learn.microsoft.com/power-bi/connect-data/incremental-refresh-overview)

### — IN-001 Same region for Power BI and Databricks (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['workspace', 'databricks'] but active modes are ['pbix']
**Reference:** [https://learn.microsoft.com/power-bi/admin/service-admin-where-is-my-tenant-located](https://learn.microsoft.com/power-bi/admin/service-admin-where-is-my-tenant-located)

### — IN-006 Tune Power BI query parallelization (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['workspace'] but active modes are ['pbix']
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-storage-mode](https://learn.microsoft.com/power-bi/transform-model/desktop-storage-mode)

### — IN-007 Enable SSO between Power BI and Databricks (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['workspace'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/integrations/configure-power-bi-sso.html](https://docs.databricks.com/integrations/configure-power-bi-sso.html)

### — IN-009 Use clustered gateways (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['workspace'] but active modes are ['pbix']
**Reference:** [https://learn.microsoft.com/data-integration/gateway/service-gateway-high-availability-clusters](https://learn.microsoft.com/data-integration/gateway/service-gateway-high-availability-clusters)

### — IN-010 Use Publish to Power BI Service from Databricks (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['workspace', 'databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/integrations/configure-power-bi-online-service.html](https://docs.databricks.com/integrations/configure-power-bi-online-service.html)

### — IN-011 Use Automatic Publishing from Unity Catalog (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: requires modes ['workspace', 'databricks'] but active modes are ['pbix']
**Reference:** [https://docs.databricks.com/integrations/configure-power-bi-online-service.html](https://docs.databricks.com/integrations/configure-power-bi-online-service.html)

## Power BI Report Design

### ⚠️ RD-005 Avoid many-to-many relationships (warn)
**Target:** small_bad
**Status:** fail
**Summary:** 1 many-to-many relationship(s) detected.
**Why it matters:** Many-to-many relationships add bridge-table complexity and can degrade query plans.
**How to fix:** Replace with a bridge dimension or denormalize at the gold layer.
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-many-to-many-relationships](https://learn.microsoft.com/power-bi/transform-model/desktop-many-to-many-relationships)
                <details><summary>Evidence</summary>

                ```json
                {
  "relationships": [
    "Fact_Sales↔Dim_Region"
  ]
}
                ```
                </details>

### ⚠️ RD-006 Use Assume Referential Integrity where valid (warn)
**Target:** small_bad
**Status:** fail
**Summary:** 1 relationship(s) eligible for Assume Referential Integrity.
**Why it matters:** ARI lets Power BI emit INNER JOIN instead of LEFT OUTER, simplifying generated SQL.
**How to fix:** If the foreign key is enforced upstream, enable Assume Referential Integrity on the relationship.
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-relationships-troubleshoot](https://learn.microsoft.com/power-bi/transform-model/desktop-relationships-troubleshoot)
                <details><summary>Evidence</summary>

                ```json
                {
  "relationships": [
    "Fact_Sales[CustomerId] → Dim_Customer[CustomerId]"
  ]
}
                ```
                </details>

### ⚠️ RD-011 Avoid DAX calculated columns and calculated tables (warn)
**Target:** small_bad
**Status:** fail
**Summary:** 1 calculated column(s); 0 calculated table(s).
**Why it matters:** Calculated columns / tables increase semantic-model size and refresh time. Doing the same work in Gold Delta is faster and shareable.
**How to fix:** Move calculated columns into the Gold view (or a derived column at ETL time). Replace calculated tables with persisted tables.
**Reference:** [https://learn.microsoft.com/power-bi/guidance/import-modeling-data-reduction](https://learn.microsoft.com/power-bi/guidance/import-modeling-data-reduction)
                <details><summary>Evidence</summary>

                ```json
                {
  "calculated_columns": [
    "Fact_Sales[RevenuePlus10]"
  ],
  "calculated_tables": []
}
                ```
                </details>

### ✅ RD-001 Limit visuals per page (pass)
**Target:** small_bad
**Status:** pass
**Summary:** Each page has ≤ 12 visuals.
**Reference:** [https://learn.microsoft.com/power-bi/guidance/power-bi-optimization](https://learn.microsoft.com/power-bi/guidance/power-bi-optimization)

### ✅ RD-002 Limit rows and columns surfaced in DirectQuery (pass)
**Target:** small_bad
**Status:** pass
**Summary:** No DirectQuery table has > 50 columns.
**Reference:** [https://learn.microsoft.com/power-bi/guidance/power-bi-optimization](https://learn.microsoft.com/power-bi/guidance/power-bi-optimization)

### ✅ RD-003 Use user-defined aggregations on large fact tables (pass)
**Target:** small_bad
**Status:** pass
**Summary:** No large unsupported fact, or aggregations already mapped.
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/aggregations-advanced](https://learn.microsoft.com/power-bi/transform-model/aggregations-advanced)

### ✅ RD-004 Enable automatic aggregations for DirectQuery (pass)
**Target:** small_bad
**Status:** pass
**Summary:** No DirectQuery tables; rule N/A.
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/aggregations-auto](https://learn.microsoft.com/power-bi/transform-model/aggregations-auto)

### ✅ RD-008 Move transformations left (prefer SQL views) (pass)
**Target:** small_bad
**Status:** pass
**Summary:** No M transformations matching the move-left heuristic.
**Reference:** [https://learn.microsoft.com/power-bi/guidance/power-query-folding](https://learn.microsoft.com/power-bi/guidance/power-query-folding)

### ✅ RD-009 Use efficient DAX patterns (pass)
**Target:** small_bad
**Status:** pass
**Summary:** No DAX smells matched.
**Reference:** [https://learn.microsoft.com/dax/best-practices/dax-aggregators](https://learn.microsoft.com/dax/best-practices/dax-aggregators)

### ✅ RD-010 Add Apply All Slicers when many slicers (pass)
**Target:** small_bad
**Status:** pass
**Summary:** No slicer-heavy pages, or Apply All Slicers enabled.
**Reference:** [https://learn.microsoft.com/power-bi/create-reports/desktop-query-reduction](https://learn.microsoft.com/power-bi/create-reports/desktop-query-reduction)

### — RD-007 Configure 'Is nullable' to match source (n/a)
**Target:** -
**Status:** not_applicable
**Summary:** Not applicable: required input CatalogState not collected
**Reference:** [https://learn.microsoft.com/power-bi/transform-model/desktop-tutorial-create-calculated-columns](https://learn.microsoft.com/power-bi/transform-model/desktop-tutorial-create-calculated-columns)
