
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

HS6_OVERALL = OUTPUT_DIR / "17_hs6_trade_overall.csv"
HS6_ANNUAL = OUTPUT_DIR / "17_hs6_trade_annual.csv"
HS6_HHI = OUTPUT_DIR / "17_hs6_concentration_hhi.csv"

EXPORT_HS9 = OUTPUT_DIR / "17_export_hs9_rankings.csv"
IMPORT_HS9 = OUTPUT_DIR / "17_import_hs9_rankings.csv"

SPECIAL_CODES = "'000000019', '000000099', '000000190'"

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

print("=" * 75)
print("JAPAN TRADE INTELLIGENCE")
print("HS6 HARMONIZED AND DIRECTIONAL HS9 ANALYSIS")
print("=" * 75)

# --------------------------------------------------
# 3. HS6 OVERALL ANALYSIS
# --------------------------------------------------

hs6_overall_query = f"""
WITH source_data AS (
    SELECT
        LEFT(hs9, 6) AS hs6_code,
        exp_imp,
        Value
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    WHERE hs9 NOT IN ({SPECIAL_CODES})
),

product_totals AS (
    SELECT
        hs6_code,

        COUNT(*) AS total_records,

        SUM(CASE WHEN exp_imp = 1
                 THEN Value ELSE 0 END) AS export_value,

        SUM(CASE WHEN exp_imp = 2
                 THEN Value ELSE 0 END) AS import_value,

        SUM(Value) AS total_trade_value

    FROM source_data
    GROUP BY hs6_code
),

shares AS (
    SELECT
        *,
        SUM(total_trade_value) OVER () AS grand_total,
        SUM(export_value) OVER () AS grand_exports,
        SUM(import_value) OVER () AS grand_imports
    FROM product_totals
)

SELECT
    hs6_code,
    total_records,
    export_value,
    import_value,
    total_trade_value,

    export_value - import_value AS trade_balance,

    ROUND(
        100.0 * total_trade_value / NULLIF(grand_total, 0), 6
    ) AS total_trade_share_pct,

    ROUND(
        100.0 * export_value / NULLIF(grand_exports, 0), 6
    ) AS export_share_pct,

    ROUND(
        100.0 * import_value / NULLIF(grand_imports, 0), 6
    ) AS import_share_pct

FROM shares
ORDER BY total_trade_value DESC
"""

con.execute(f"""
COPY ({hs6_overall_query})
TO '{HS6_OVERALL.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("\nHS6 overall analysis saved.")

# --------------------------------------------------
# 4. ANNUAL HS6 ANALYSIS
# --------------------------------------------------

hs6_annual_query = f"""
WITH source_data AS (
    SELECT
        CAST(FLOOR(ym / 100) AS INTEGER) AS year,
        LEFT(hs9, 6) AS hs6_code,
        exp_imp,
        Value
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    WHERE hs9 NOT IN ({SPECIAL_CODES})
)

SELECT
    year,
    hs6_code,

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
GROUP BY year, hs6_code
ORDER BY year, total_trade_value DESC
"""

con.execute(f"""
COPY ({hs6_annual_query})
TO '{HS6_ANNUAL.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Annual HS6 analysis saved.")

# --------------------------------------------------
# 5. ANNUAL HS6 PRODUCT CONCENTRATION
# --------------------------------------------------

hs6_hhi_query = f"""
WITH source_data AS (
    SELECT
        CAST(FLOOR(ym / 100) AS INTEGER) AS year,
        LEFT(hs9, 6) AS hs6_code,
        exp_imp,
        Value
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    WHERE hs9 NOT IN ({SPECIAL_CODES})
),

annual_product AS (
    SELECT
        year,
        hs6_code,

        SUM(CASE WHEN exp_imp = 1
                 THEN Value ELSE 0 END) AS exports,

        SUM(CASE WHEN exp_imp = 2
                 THEN Value ELSE 0 END) AS imports,

        SUM(Value) AS total_trade

    FROM source_data
    GROUP BY year, hs6_code
),

annual_totals AS (
    SELECT
        year,
        SUM(exports) AS year_exports,
        SUM(imports) AS year_imports,
        SUM(total_trade) AS year_total_trade,
        COUNT(*) AS product_count
    FROM annual_product
    GROUP BY year
),

product_shares AS (
    SELECT
        p.year,
        p.hs6_code,
        t.product_count,

        p.total_trade / NULLIF(t.year_total_trade, 0)
            AS total_share,

        p.exports / NULLIF(t.year_exports, 0)
            AS export_share,

        p.imports / NULLIF(t.year_imports, 0)
            AS import_share

    FROM annual_product p
    JOIN annual_totals t USING (year)
)

SELECT
    year,
    MAX(product_count) AS product_count,

    ROUND(SUM(total_share * total_share) * 10000, 2)
        AS total_hs6_hhi,

    ROUND(SUM(export_share * export_share) * 10000, 2)
        AS export_hs6_hhi,

    ROUND(SUM(import_share * import_share) * 10000, 2)
        AS import_hs6_hhi

FROM product_shares
GROUP BY year
ORDER BY year
"""

con.execute(f"""
COPY ({hs6_hhi_query})
TO '{HS6_HHI.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Annual HS6 concentration analysis saved.")

# --------------------------------------------------
# 6. EXPORT-ONLY HS9 ANALYSIS
# --------------------------------------------------

export_hs9_query = f"""
WITH product_totals AS (
    SELECT
        hs9 AS hs9_code,

        COUNT(*) AS total_records,
        COUNT(DISTINCT ym) AS active_months,
        SUM(Value) AS export_value

    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    WHERE exp_imp = 1
      AND hs9 NOT IN ({SPECIAL_CODES})
    GROUP BY hs9
),

shares AS (
    SELECT
        *,
        SUM(export_value) OVER () AS grand_exports
    FROM product_totals
)

SELECT
    hs9_code,
    total_records,
    active_months,
    export_value,

    ROUND(
        100.0 * export_value / NULLIF(grand_exports, 0), 6
    ) AS export_share_pct

FROM shares
ORDER BY export_value DESC
"""

con.execute(f"""
COPY ({export_hs9_query})
TO '{EXPORT_HS9.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Export HS9 analysis saved.")

# --------------------------------------------------
# 7. IMPORT-ONLY HS9 ANALYSIS
# --------------------------------------------------

import_hs9_query = f"""
WITH product_totals AS (
    SELECT
        hs9 AS hs9_code,

        COUNT(*) AS total_records,
        COUNT(DISTINCT ym) AS active_months,
        SUM(Value) AS import_value

    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    WHERE exp_imp = 2
      AND hs9 NOT IN ({SPECIAL_CODES})
    GROUP BY hs9
),

shares AS (
    SELECT
        *,
        SUM(import_value) OVER () AS grand_imports
    FROM product_totals
)

SELECT
    hs9_code,
    total_records,
    active_months,
    import_value,

    ROUND(
        100.0 * import_value / NULLIF(grand_imports, 0), 6
    ) AS import_share_pct

FROM shares
ORDER BY import_value DESC
"""

con.execute(f"""
COPY ({import_hs9_query})
TO '{IMPORT_HS9.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Import HS9 analysis saved.")

# --------------------------------------------------
# 8. VALIDATION
# --------------------------------------------------

def count_rows(path):
    return con.execute(
        f"SELECT COUNT(*) FROM read_csv_auto('{path.as_posix()}')"
    ).fetchone()[0]


print("\nVALIDATION")
print("-" * 75)

print(f"Unique HS6 codes: {count_rows(HS6_OVERALL)}")
print(f"Annual HS6 observations: {count_rows(HS6_ANNUAL)}")
print(f"Annual HS6 HHI observations: {count_rows(HS6_HHI)}")
print(f"Export HS9 codes: {count_rows(EXPORT_HS9)}")
print(f"Import HS9 codes: {count_rows(IMPORT_HS9)}")

print("\nTOP 20 HS6 PRODUCTS BY TOTAL TRADE VALUE")
print("-" * 75)

print(
    con.execute(f"""
        SELECT
            hs6_code,
            export_value,
            import_value,
            total_trade_value,
            trade_balance,
            total_trade_share_pct
        FROM read_csv_auto('{HS6_OVERALL.as_posix()}')
        ORDER BY total_trade_value DESC
        LIMIT 20
    """).df().to_string(index=False)
)

print("\nTOP 10 EXPORT HS9 CODES")
print("-" * 75)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{EXPORT_HS9.as_posix()}')
        ORDER BY export_value DESC
        LIMIT 10
    """).df().to_string(index=False)
)

print("\nTOP 10 IMPORT HS9 CODES")
print("-" * 75)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{IMPORT_HS9.as_posix()}')
        ORDER BY import_value DESC
        LIMIT 10
    """).df().to_string(index=False)
)

print("\nANNUAL HS6 CONCENTRATION - FIRST 10 YEARS")
print("-" * 75)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{HS6_HHI.as_posix()}')
        ORDER BY year
        LIMIT 10
    """).df().to_string(index=False)
)

print("\nMOST CONCENTRATED HS6 YEARS")
print("-" * 75)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{HS6_HHI.as_posix()}')
        ORDER BY total_hs6_hhi DESC
        LIMIT 5
    """).df().to_string(index=False)
)

print("\nLEAST CONCENTRATED HS6 YEARS")
print("-" * 75)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{HS6_HHI.as_posix()}')
        ORDER BY total_hs6_hhi
        LIMIT 5
    """).df().to_string(index=False)
)

print("\nOUTPUT FILES")
print("-" * 75)

for file in [
    HS6_OVERALL,
    HS6_ANNUAL,
    HS6_HHI,
    EXPORT_HS9,
    IMPORT_HS9
]:
    print(file)

print("\n" + "=" * 75)
print(f"Execution time: {time.time() - start:.2f} seconds")
print("HS6 AND DIRECTIONAL HS9 ANALYSIS COMPLETED")
print("=" * 75)

con.close()
