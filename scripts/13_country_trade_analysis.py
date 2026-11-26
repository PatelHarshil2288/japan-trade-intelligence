
from pathlib import Path
import duckdb
import time

# --------------------------------------------------
# 1. PATHS
# --------------------------------------------------

ROOT = Path(r"D:\Japan_Trade_Intelligence")

PARQUET_FILE = (
    ROOT / "data" / "processed" / "parquet" / "japan_trade.parquet"
)

OUTPUT_DIR = ROOT / "data" / "processed" / "aggregated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OVERALL_OUTPUT = OUTPUT_DIR / "13_country_trade_overall.csv"
ANNUAL_OUTPUT = OUTPUT_DIR / "13_country_trade_annual.csv"
HHI_OUTPUT = OUTPUT_DIR / "13_country_concentration_hhi.csv"

# --------------------------------------------------
# 2. DUCKDB
# --------------------------------------------------

con = duckdb.connect()
con.execute("SET memory_limit = '4GB'")
con.execute("SET threads = 4")
con.execute(
    f"SET temp_directory = '{(ROOT / 'temp').as_posix()}'"
)

start = time.time()

print("=" * 70)
print("JAPAN TRADE INTELLIGENCE - COUNTRY ANALYSIS")
print("=" * 70)

# --------------------------------------------------
# 3. OVERALL PARTNER ANALYSIS: 1988-2020
# --------------------------------------------------

overall_query = f"""
WITH country_totals AS (
    SELECT
        CAST(Country AS VARCHAR) AS country_code,

        COUNT(*) AS total_records,
        COUNT(DISTINCT ym) AS active_months,

        SUM(CASE WHEN exp_imp = 1
                 THEN Value ELSE 0 END) AS export_value,

        SUM(CASE WHEN exp_imp = 2
                 THEN Value ELSE 0 END) AS import_value,

        SUM(Value) AS total_trade_value

    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    GROUP BY Country
),

shares AS (
    SELECT
        *,
        SUM(total_trade_value) OVER () AS grand_total,
        SUM(export_value) OVER () AS grand_exports,
        SUM(import_value) OVER () AS grand_imports
    FROM country_totals
)

SELECT
    country_code,
    total_records,
    active_months,
    export_value,
    import_value,
    total_trade_value,

    export_value - import_value AS trade_balance,

    ROUND(
        100.0 * total_trade_value / grand_total, 6
    ) AS total_trade_share_pct,

    ROUND(
        100.0 * export_value / grand_exports, 6
    ) AS export_share_pct,

    ROUND(
        100.0 * import_value / grand_imports, 6
    ) AS import_share_pct

FROM shares
ORDER BY total_trade_value DESC
"""

con.execute(f"""
COPY ({overall_query})
TO '{OVERALL_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("\nOverall country analysis saved.")


# --------------------------------------------------
# 4. ANNUAL PARTNER ANALYSIS
# --------------------------------------------------

annual_query = f"""
WITH source_data AS (
    SELECT
        CAST(FLOOR(ym / 100) AS INTEGER) AS year,
        Country,
        exp_imp,
        Value
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
)

SELECT
    year,
    CAST(Country AS VARCHAR) AS country_code,

    COUNT(*) AS total_records,

    SUM(CASE WHEN exp_imp = 1
             THEN Value ELSE 0 END) AS export_value,

    SUM(CASE WHEN exp_imp = 2
             THEN Value ELSE 0 END) AS import_value,

    SUM(Value) AS total_trade_value,

    SUM(CASE WHEN exp_imp = 1
             THEN Value ELSE 0 END)
    -
    SUM(CASE WHEN exp_imp = 2
             THEN Value ELSE 0 END) AS trade_balance

FROM source_data
GROUP BY year, Country
ORDER BY year, total_trade_value DESC
"""

con.execute(f"""
COPY ({annual_query})
TO '{ANNUAL_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Annual country analysis saved.")


# --------------------------------------------------
# 5. ANNUAL COUNTRY CONCENTRATION: HHI
# --------------------------------------------------

hhi_query = f"""
WITH source_data AS (
    SELECT
        CAST(FLOOR(ym / 100) AS INTEGER) AS year,
        Country,
        exp_imp,
        Value
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
),

annual_country AS (
    SELECT
        year,
        Country,

        SUM(CASE WHEN exp_imp = 1
                 THEN Value ELSE 0 END) AS exports,

        SUM(CASE WHEN exp_imp = 2
                 THEN Value ELSE 0 END) AS imports,

        SUM(Value) AS total_trade

    FROM source_data
    GROUP BY year, Country
),

annual_totals AS (
    SELECT
        year,
        SUM(exports) AS year_exports,
        SUM(imports) AS year_imports,
        SUM(total_trade) AS year_total_trade,
        COUNT(*) AS partner_count
    FROM annual_country
    GROUP BY year
),

partner_shares AS (
    SELECT
        a.year,
        a.Country,
        t.partner_count,

        a.total_trade / NULLIF(t.year_total_trade, 0)
            AS total_share,

        a.exports / NULLIF(t.year_exports, 0)
            AS export_share,

        a.imports / NULLIF(t.year_imports, 0)
            AS import_share

    FROM annual_country a
    JOIN annual_totals t USING (year)
)

SELECT
    year,
    MAX(partner_count) AS partner_count,

    ROUND(
        SUM(total_share * total_share) * 10000, 2
    ) AS total_trade_hhi,

    ROUND(
        SUM(export_share * export_share) * 10000, 2
    ) AS export_hhi,

    ROUND(
        SUM(import_share * import_share) * 10000, 2
    ) AS import_hhi

FROM partner_shares
GROUP BY year
ORDER BY year
"""

con.execute(f"""
COPY ({hhi_query})
TO '{HHI_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Annual HHI analysis saved.")


# --------------------------------------------------
# 6. VALIDATION AND TOP PARTNERS
# --------------------------------------------------

overall_count = con.execute(f"""
    SELECT COUNT(*)
    FROM read_csv_auto('{OVERALL_OUTPUT.as_posix()}')
""").fetchone()[0]

annual_count = con.execute(f"""
    SELECT COUNT(*)
    FROM read_csv_auto('{ANNUAL_OUTPUT.as_posix()}')
""").fetchone()[0]

hhi_count = con.execute(f"""
    SELECT COUNT(*)
    FROM read_csv_auto('{HHI_OUTPUT.as_posix()}')
""").fetchone()[0]

print("\nVALIDATION")
print("-" * 70)
print(f"Unique partner codes: {overall_count}")
print(f"Annual partner observations: {annual_count}")
print(f"Annual HHI observations: {hhi_count}")
print("Expected HHI observations: 33")

print("\nTOP 15 TRADING PARTNERS BY TOTAL VALUE")
print("-" * 70)

print(
    con.execute(f"""
        SELECT
            country_code,
            total_records,
            export_value,
            import_value,
            total_trade_value,
            trade_balance,
            total_trade_share_pct
        FROM read_csv_auto('{OVERALL_OUTPUT.as_posix()}')
        ORDER BY total_trade_value DESC
        LIMIT 15
    """).df().to_string(index=False)
)

print("\nANNUAL HHI SUMMARY")
print("-" * 70)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{HHI_OUTPUT.as_posix()}')
        ORDER BY year
        LIMIT 10
    """).df().to_string(index=False)
)

print("\nMOST CONCENTRATED YEARS")
print("-" * 70)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{HHI_OUTPUT.as_posix()}')
        ORDER BY total_trade_hhi DESC
        LIMIT 5
    """).df().to_string(index=False)
)

print("\nLEAST CONCENTRATED YEARS")
print("-" * 70)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{HHI_OUTPUT.as_posix()}')
        ORDER BY total_trade_hhi
        LIMIT 5
    """).df().to_string(index=False)
)

print("\n" + "=" * 70)
print(f"Execution time: {time.time() - start:.2f} seconds")
print("COUNTRY TRADE ANALYSIS COMPLETED")
print("=" * 70)

con.close()
