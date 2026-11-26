# Japan Semiconductor Trade Intelligence

## Project overview

Japan Semiconductor Trade Intelligence is a data analysis project examining Japan's trade changes between 2017 and 2020 across three selected semiconductor HS6 categories:

- 854231
- 854232
- 854239

The project compares export and import values, evaluates country-level changes, decomposes net changes by HS6 code, and presents the results through an interactive dashboard.

## Key findings

| Metric | Change, 2017–2020 |
|---|---:|
| Selected-category exports | +¥0.048024 trillion |
| Selected-category imports | −¥0.170162 trillion |
| Selected-category trade balance | +¥0.218186 trillion |

The largest export increases among the reported country changes included Taiwan, Viet Nam, and Malaysia.

The largest export decreases included the People's Republic of China, Republic of Korea, and the United States of America.

For imports, Taiwan had the largest increase, while the Republic of Korea, United States, and Singapore had the largest decreases.

## HS6 contribution analysis

### Exports
- HS6 854232: +¥0.214842 trillion
- HS6 854239: −¥0.019117 trillion
- HS6 854231: −¥0.147701 trillion

### Imports
- HS6 854231: +¥0.070665 trillion
- HS6 854232: −¥0.015224 trillion
- HS6 854239: −¥0.225603 trillion

## Data quality and validation

Phase 65 cross-phase reconciliation completed with PASS status across all eight checks.

Validation covered:
- Phase 59 country-direction totals against Phase 61
- Phase 61 totals against Phase 62
- HS6 component reconciliation
- Phase 62 totals against Phase 63 heatmap aggregates and country rankings
- Selected HS6 code coverage
- Heatmap row-count consistency
- Export/import directional totals

## Project outputs

- Interactive dashboard: `semiconductor_trade_dashboard_2017_2020.html`
- Findings report: `66_semiconductor_findings_report.md`
- Country-level changes: `66_semiconductor_country_changes.csv`
- HS6 directional contributions: `66_semiconductor_hs6_directional_contributions.csv`
- Cross-phase QA summary: `65_semiconductor_dashboard_qa_summary.txt`

## Methodology and limitations

This is a descriptive comparison of 2017 and 2020, not a causal analysis.

The findings cover only HS6 854231, 854232, and 854239. They should not be generalized to all semiconductor trade or interpreted as a continuous annual trend.

Country-level changes indicate where the selected-category net changes were recorded; they do not establish the reasons behind those changes.

## Portfolio description

Built a Japan semiconductor trade intelligence workflow that reconciles country-level trade changes across multiple analytical stages, decomposes net changes by HS6 product code, validates outputs through cross-phase QA checks, and presents the results in an interactive dashboard.
