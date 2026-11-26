# Japan Trade Intelligence

A large-scale data engineering and trade analytics project built around Japan's customs trade records from 1988 to 2020.

The project explores how Japan's international trade evolved across time, trading partners, and product classifications, with a focus on data quality, HS classification analysis, and reproducible analytical workflows.

## Project Overview

The source dataset contains approximately **113.6 million records** covering:

- **Period:** January 1988 - December 2020
- **Trading partners:** 242 unique countries or territories
- **Source format:** CSV and SQLite
- **Analytical warehouse:** Parquet

The original source files and generated data are not included in this repository because of their size. Scripts expect the project data to be available in the local directory structure.

## Key Technical Areas

- Large-scale data inspection and profiling
- Data integrity and quality validation
- Trade quantity and value analysis
- Annual and monthly trade trends
- Country and trading-partner analysis
- HS product classification analysis
- HS code stability and revision impact investigation
- HS concordance and mapping diagnostics
- Product-level and chapter-level analysis
- Semiconductor trade analysis and dashboard development

## Semiconductor Case Study

A focused analytical case study compares Japan's semiconductor-related trade in **2017 and 2020** for the following HS6 codes:

| HS6 code | Product category |
|---|---|
| 854231 | Electronic integrated circuits â€” processors and controllers |
| 854232 | Electronic integrated circuits â€” memories |
| 854239 | Electronic integrated circuits â€” other |

The analysis includes country-level shifts, HS6 contribution analysis, directional trade comparisons, reconciliation checks, and an interactive dashboard.

The case study is intentionally limited to these three HS6 codes and the two comparison years. It should not be interpreted as a complete analysis of all semiconductor trade or as evidence of causal effects.

## Repository Structure

```text
Japan_Trade_Intelligence/
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/             # Original source data (not tracked)
â”‚   â”œâ”€â”€ processed/       # Generated analytical data (not tracked)
â”‚   â””â”€â”€ reference/       # Reference data (not tracked)
â”œâ”€â”€ scripts/             # Numbered analysis and validation scripts
â”œâ”€â”€ reports/             # Selected reports and portfolio artifacts
â”œâ”€â”€ logs/                # Local execution logs (not tracked)
â”œâ”€â”€ temp/                # Temporary files (not tracked)
â”œâ”€â”€ .gitignore
â””â”€â”€ README.md
