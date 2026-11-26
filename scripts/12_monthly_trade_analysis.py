
from pathlib import Path
import duckdb
import time

# --------------------------------------------------
# 1. PROJECT PATHS
# --------------------------------------------------

ROOT = Path(r"D:\Japan_Trade_Intelligence")

PARQUET_FILE = (
    ROOT / "data" / "processed" / "parquet" / "japan_trade.parquet"
)

OUTPUT_DIR = ROOT / "data" / "processed" / "aggregated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MONTHLY_OUTPUT = OUTPUT_DIR / "12_monthly_trade_analysis.csv"
SEASONAL_OUTPUT = OUTPUT_DIR / "12_monthly_seasonality.csv"

# --------------------------------------------------
# 2. DUCKDB CONFIGURATION
# --------------------------------------------------

con = duckdb.connect()

con.execute("SET memory_limit = '4GB'")
con.execute("SET threads = 4")
con.execute(
    f"SET temp_directory = '{(ROOT / 'temp').as_posix()}'"
)

start = time.time()

print("=" * 65)
print("JAPAN TRADE INTELLIGENCE - MONTHLY ANALYSIS")
print("=" * 65)

# --------------------------------------------------
# 3. MONTHLY TRADE AGGREGATION
# --------------------------------------------------

monthly_query = f"""
WITH monthly AS (
    SELECT
        ym,
        CAST(FLOOR(ym / 100) AS INTEGER) AS year,
        CAST(ym % 100 AS INTEGER) AS month,

        COUNT(*) AS full_records,

        SUM(CASE WHEN exp_imp = 1
                 THEN Value ELSE 0 END) AS full_export_value,

        SUM(CASE WHEN exp_imp = 2
                 THEN Value ELSE 0 END) AS full_import_value,

        SUM(Value) AS full_total_trade_value,

        SUM(CASE WHEN exp_imp = 1
                 THEN Value ELSE 0 END)
        -
        SUM(CASE WHEN exp_imp = 2
                 THEN Value ELSE 0 END) AS full_trade_balance,

        SUM(CASE
            WHEN hs9 NOT IN (
                '000000019',
                '000000099',
                '000000190'
            )
            THEN 1 ELSE 0
        END) AS ordinary_records,

        SUM(CASE
            WHEN exp_imp = 1
             AND hs9 NOT IN (
                '000000019',
                '000000099',
                '000000190'
             )
            THEN Value ELSE 0
        END) AS ordinary_export_value,

        SUM(CASE
            WHEN exp_imp = 2
             AND hs9 NOT IN (
                '000000019',
                '000000099',
                '000000190'
             )
            THEN Value ELSE 0
        END) AS ordinary_import_value

    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    GROUP BY ym
)

SELECT
    *,
    ordinary_export_value - ordinary_import_value
        AS ordinary_trade_balance

FROM monthly
ORDER BY ym
"""

con.execute(f"""
COPY ({monthly_query})
TO '{MONTHLY_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("\nMonthly aggregation completed.")
print(f"Saved: {MONTHLY_OUTPUT}")

# --------------------------------------------------
# 4. CALENDAR-MONTH SEASONALITY
# --------------------------------------------------

seasonality_query = f"""
SELECT
    month,

    COUNT(*) AS number_of_years,

    ROUND(AVG(full_export_value), 2)
        AS avg_monthly_export_value,

    ROUND(AVG(full_import_value), 2)
        AS avg_monthly_import_value,

    ROUND(AVG(full_total_trade_value), 2)
        AS avg_monthly_total_trade_value,

    ROUND(AVG(full_trade_balance), 2)
        AS avg_monthly_trade_balance,

    ROUND(AVG(ordinary_trade_balance), 2)
        AS avg_ordinary_trade_balance

FROM read_csv_auto('{MONTHLY_OUTPUT.as_posix()}')
GROUP BY month
ORDER BY month
"""

con.execute(f"""
COPY ({seasonality_query})
TO '{SEASONAL_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("\nSeasonality aggregation completed.")
print(f"Saved: {SEASONAL_OUTPUT}")

# --------------------------------------------------
# 5. VALIDATION
# --------------------------------------------------

monthly_count = con.execute(f"""
    SELECT COUNT(*)
    FROM read_csv_auto('{MONTHLY_OUTPUT.as_posix()}')
""").fetchone()[0]

print("\nVALIDATION")
print("-" * 65)
print(f"Monthly records: {monthly_count}")
print(f"Expected months: 396")

print("\nMONTHLY OUTPUT SAMPLE")
print("-" * 65)

print(
    con.execute(f"""
        SELECT
            year,
            month,
            full_export_value,
            full_import_value,
            full_trade_balance
        FROM read_csv_auto('{MONTHLY_OUTPUT.as_posix()}')
        ORDER BY ym
        LIMIT 12
    """).df().to_string(index=False)
)

print("\nSEASONALITY SUMMARY")
print("-" * 65)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{SEASONAL_OUTPUT.as_posix()}')
        ORDER BY month
    """).df().to_string(index=False)
)

print("\n" + "=" * 65)
print(f"Execution time: {time.time() - start:.2f} seconds")
print("MONTHLY TRADE ANALYSIS COMPLETED")
print("=" * 65)

con.close()

