# Japan Trade Intelligence

**A large-scale data engineering and analytics project analyzing Japan's international trade from 1988 to 2020.**

Japan Trade Intelligence transforms more than **113 million trade records** into a structured Bronze–Silver–Gold data platform using Databricks, Apache Spark, and Delta Lake. The project includes data quality validation, analytical aggregation, and an interactive dashboard for exploring long-term trade patterns.

## Project Overview

| Metric | Value |
|---|---:|
| Historical coverage | 1988–2020 |
| Years covered | 33 |
| Trade records | 113,607,322 |
| Countries / country codes | 242 |
| Total recorded trade value | 3.68 trillion |
| Source format | Parquet |
| Processing platform | Databricks |

## Architecture

```text
Source Parquet Dataset
        |
        v
Databricks Volume
        |
        v
Bronze Layer
Raw trade records stored as Delta
        |
        v
Silver Layer
Validated records + data quality flags
        |
        v
Gold Layer
Yearly / Country / HS9 aggregates
        |
        v
Interactive Databricks Dashboard
```

### Medallion Architecture

**Bronze — Raw ingestion**

- Ingested the source Parquet dataset into Delta Lake.
- Partitioned the Bronze table by year.
- Validated the ingested record count against the source.

**Silver — Data quality and validation**

- Preserved the original trade records.
- Added quality flags for quantity fields.
- Identified records with zero quantities without automatically dropping them.
- Checked year and month consistency, missing values, and field formats.

**Gold — Analytical data marts**

Created aggregated tables for:

- Yearly trade trends
- Country-level trade analysis
- HS9 commodity-level trade analysis

Each aggregation includes trade value and quantity measures, grouped by trade direction where applicable.

## Data Quality and Reconciliation

The project includes validation checks for:

- Null and missing values
- Invalid year-month values
- Year-month consistency
- HS9 code length
- Negative quantity and value records
- Zero-quantity records
- Bronze and Silver row-count consistency
- Gold aggregation reconciliation

### Reconciliation Results

| Validation | Result |
|---|---:|
| Silver record count | 113,607,322 |
| Gold yearly aggregated record count | 113,607,322 |
| Silver total trade value | 3,681,820,443,472 |
| Gold total trade value | 3,681,820,443,472 |

The Silver and Gold totals reconcile exactly.

Zero-quantity records were retained and flagged for analysis rather than removed without investigation.

## Databricks Tables

Catalog: `workspace`

Schema: `japan_trade_intelligence`

| Layer | Table |
|---|---|
| Bronze | `bronze_japan_trade` |
| Silver | `silver_japan_trade` |
| Gold | `gold_yearly_trade` |
| Gold | `gold_country_trade` |
| Gold | `gold_hs9_trade` |

## Dashboard

The published Databricks dashboard provides:

- Japan's yearly trade value trend
- Top trading countries
- Top HS9 commodity codes
- Total recorded trade value
- Total trade records
- Years covered
- Latest year in the dataset

Dashboard title: **Japan Trade Intelligence | 1988–2020**

## Technology Stack

- Databricks Free Edition
- Apache Spark / PySpark
- Delta Lake
- SQL
- Parquet
- Bronze–Silver–Gold Medallion Architecture
- Databricks Dashboards
- Git and GitHub

## Repository

GitHub: https://github.com/PatelHarshil2288/japan-trade-intelligence

## Project Goals

This project demonstrates practical data engineering skills in:

- Large-scale data ingestion
- Distributed data processing
- Lakehouse architecture
- Data quality engineering
- Delta table creation and partitioning
- Analytical data modeling
- Aggregation and reconciliation
- Dashboard development

## Notes

The dataset covers historical trade data through 2020. Trade-direction codes (`exp_imp`) are retained as source codes and should be interpreted using the dataset's official documentation.
