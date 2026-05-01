# pbix fixtures

## Synthetic `.pbip` directories

Real `.pbix` binaries require Power BI Desktop on Windows and cannot be authored
in this environment. Instead, two synthetic `.pbip` project directories are
checked in. Each contains a `SemanticModel/model.bim` file with hand-authored
JSON conforming to the Microsoft Tabular Object Model (TOM) schema (minimal
subset sufficient for PbixCollector tests).

### `small_good.pbip/`
- **Tables**: `Fact_Sales` (Import mode) + `Dim_Customer` (Dual mode).
- **Relationship**: `Fact_Sales[CustomerId] → Dim_Customer[CustomerId]`,
  cardinality `many-to-one`, single cross-filter,
  `relyOnReferentialIntegrity = true`.
- **Measure**: `TotalRevenue = SUM(Fact_Sales[Revenue])`.
- No calculated columns or calculated tables.
- Expected collector behaviour: parses cleanly; zero many-to-many
  relationships; one measure named `TotalRevenue`.

### `small_bad.pbip/`
Same shape as `small_good`, plus deliberate violations:
- **Many-to-many relationship**: `Fact_Sales[Region] ↔ Dim_Region[RegionId]`
  (triggers RD-005).
- **Calculated column**: `Fact_Sales[RevenuePlus10]` with `type = "calculated"`
  (triggers RD-011 when that rule is implemented).
- `relyOnReferentialIntegrity = false` on all relationships (triggers RD-006).
- Nullable `OrderId` on `Fact_Sales` (triggers RD-007).

## Mocking strategy for `.pbix` tests

`pbixray.PBIXRay` requires a real `.pbix` binary (a zip produced by Power BI
Desktop on Windows) and cannot be used in CI without such a file. Tests that
exercise `PbixCollector._collect_pbix` therefore patch `pbixray.PBIXRay` with
`unittest.mock.patch("pbixray.PBIXRay", ...)`, supplying a `MagicMock` that
exposes the same attribute interface (`tables`, `relationships`, `dax_measures`,
`dax_columns`, `dax_tables`, `statistics`).

See `tests/collectors/test_pbix.py` for the concrete mock setup.
