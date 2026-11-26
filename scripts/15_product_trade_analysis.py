
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

OVERALL_OUTPUT = OUTPUT_DIR / "15_product_trade_overall.csv"
ANNUAL_OUTPUT = OUTPUT_DIR / "15_product_trade_annual.csv"
HHI_OUTPUT = OUTPUT_DIR / "15_product_concentration_hhi.csv"
CHANGE_OUTPUT = OUTPUT_DIR / "15_product_change_1988_2020.csv"
SPECIAL_OUTPUT = OUTPUT_DIR / "15_special_product_codes.csv"

SPECIAL_CODES = (
    "'000000019', '000000099', '000000190'"
)

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

print("=" * 70)
print("JAPAN TRADE INTELLIGENCE")
print("PRODUCT AND HS9 TRADE ANALYSIS")
print("=" * 70)

# --------------------------------------------------
# 3. OVERALL PRODUCT ANALYSIS
# --------------------------------------------------

overall_query = f"""
WITH product_totals AS (
    SELECT
        hs9 AS hs9_code,

        COUNT(*) AS total_records,
        COUNT(DISTINCT ym) AS active_months,

        SUM(CASE WHEN exp_imp = 1
                 THEN Value ELSE 0 END) AS export_value,

        SUM(CASE WHEN exp_imp = 2
                 THEN Value ELSE 0 END) AS import_value,

        SUM(Value) AS total_trade_value

    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    WHERE hs9 NOT IN ({SPECIAL_CODES})
    GROUP BY hs9
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
    hs9_code,
    total_records,
    active_months,
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
COPY ({overall_query})
TO '{OVERALL_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("\nOverall product analysis saved.")


# --------------------------------------------------
# 4. ANNUAL PRODUCT ANALYSIS
# --------------------------------------------------

annual_query = f"""
WITH source_data AS (
    SELECT
        CAST(FLOOR(ym / 100) AS INTEGER) AS year,
        hs9,
        exp_imp,
        Value
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    WHERE hs9 NOT IN ({SPECIAL_CODES})
)

SELECT
    year,
    hs9 AS hs9_code,

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
GROUP BY year, hs9
ORDER BY year, total_trade_value DESC
"""

con.execute(f"""
COPY ({annual_query})
TO '{ANNUAL_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Annual product analysis saved.")

# --------------------------------------------------
# 5. ANNUAL PRODUCT CONCENTRATION: HHI
# --------------------------------------------------

hhi_query = f"""
WITH source_data AS (
    SELECT
        CAST(FLOOR(ym / 100) AS INTEGER) AS year,
        hs9,
        exp_imp,
        Value
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    WHERE hs9 NOT IN ({SPECIAL_CODES})
),

annual_product AS (
    SELECT
        year,
        hs9,

        SUM(CASE WHEN exp_imp = 1
                 THEN Value ELSE 0 END) AS exports,

        SUM(CASE WHEN exp_imp = 2
                 THEN Value ELSE 0 END) AS imports,

        SUM(Value) AS total_trade

    FROM source_data
    GROUP BY year, hs9
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
        p.hs9,
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
        AS total_product_hhi,

    ROUND(SUM(export_share * export_share) * 10000, 2)
        AS export_product_hhi,

    ROUND(SUM(import_share * import_share) * 10000, 2)
        AS import_product_hhi

FROM product_shares
GROUP BY year
ORDER BY year
"""

con.execute(f"""
COPY ({hhi_query})
TO '{HHI_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Product concentration analysis saved.")


# --------------------------------------------------
# 6. PRODUCT SHARE CHANGE: 1988 VS 2020
# --------------------------------------------------

change_query = f"""
WITH source_data AS (
    SELECT
        CAST(FLOOR(ym / 100) AS INTEGER) AS year,
        hs9,
        Value
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    WHERE hs9 NOT IN ({SPECIAL_CODES})
),

annual_totals AS (
    SELECT
        year,
        hs9,
        SUM(Value) AS product_value
    FROM source_data
    WHERE year IN (1988, 2020)
    GROUP BY year, hs9
),

year_shares AS (
    SELECT
        *,
        100.0 * product_value /
        SUM(product_value) OVER (PARTITION BY year)
            AS product_share_pct
    FROM annual_totals
),

start_year AS (
    SELECT
        hs9 AS hs9_code,
        product_value AS value_1988,
        product_share_pct AS share_1988
    FROM year_shares
    WHERE year = 1988
),

end_year AS (
    SELECT
        hs9 AS hs9_code,
        product_value AS value_2020,
        product_share_pct AS share_2020
    FROM year_shares
    WHERE year = 2020
)

SELECT
    COALESCE(s.hs9_code, e.hs9_code) AS hs9_code,

    s.value_1988,
    e.value_2020,

    s.share_1988,
    e.share_2020,

    e.share_2020 - s.share_1988
        AS share_change_percentage_points,

    CASE
        WHEN s.hs9_code IS NULL THEN 'New in 2020'
        WHEN e.hs9_code IS NULL THEN 'Not present in 2020'
        ELSE 'Present in both years'
    END AS presence_status

FROM start_year s
FULL OUTER JOIN end_year e
    ON s.hs9_code = e.hs9_code

ORDER BY share_change_percentage_points DESC NULLS LAST
"""

con.execute(f"""
COPY ({change_query})
TO '{CHANGE_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Product share change analysis saved.")


# --------------------------------------------------
# 7. SPECIAL CUSTOMS CODES
# --------------------------------------------------

special_query = f"""
WITH source_data AS (
    SELECT
        CAST(FLOOR(ym / 100) AS INTEGER) AS year,
        hs9,
        exp_imp,
        Value
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
    WHERE hs9 IN ({SPECIAL_CODES})
)

SELECT
    hs9 AS hs9_code,
    year,
    exp_imp AS trade_type,

    COUNT(*) AS total_records,
    SUM(Value) AS total_value

FROM source_data
GROUP BY hs9, year, exp_imp
ORDER BY hs9, year, exp_imp
"""

con.execute(f"""
COPY ({special_query})
TO '{SPECIAL_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Special customs code analysis saved.")


# --------------------------------------------------
# 8. VALIDATION
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

change_count = con.execute(f"""
    SELECT COUNT(*)
    FROM read_csv_auto('{CHANGE_OUTPUT.as_posix()}')
""").fetchone()[0]

print("\nVALIDATION")
print("-" * 70)
print(f"Ordinary HS9 product codes: {overall_count}")
print(f"Annual product observations: {annual_count}")
print(f"Annual product HHI observations: {hhi_count}")
print(f"1988-2020 product comparison codes: {change_count}")
print("Expected HHI observations: 33")

# --------------------------------------------------
# 9. TOP 20 PRODUCTS
# --------------------------------------------------

print("\nTOP 20 PRODUCTS BY TOTAL TRADE VALUE")
print("-" * 70)

print(
    con.execute(f"""
        SELECT
            hs9_code,
            total_records,
            export_value,
            import_value,
            total_trade_value,
            trade_balance,
            total_trade_share_pct
        FROM read_csv_auto('{OVERALL_OUTPUT.as_posix()}')
        ORDER BY total_trade_value DESC
        LIMIT 20
    """).df().to_string(index=False)
)

# --------------------------------------------------
# 10. TOP EXPORT PRODUCTS
# --------------------------------------------------

print("\nTOP 10 EXPORT PRODUCTS")
print("-" * 70)

print(
    con.execute(f"""
        SELECT
            hs9_code,
            export_value,
            export_share_pct
        FROM read_csv_auto('{OVERALL_OUTPUT.as_posix()}')
        ORDER BY export_value DESC
        LIMIT 10
    """).df().to_string(index=False)
)

# --------------------------------------------------
# 11. TOP IMPORT PRODUCTS
# --------------------------------------------------

print("\nTOP 10 IMPORT PRODUCTS")
print("-" * 70)

print(
    con.execute(f"""
        SELECT
            hs9_code,
            import_value,
            import_share_pct
        FROM read_csv_auto('{OVERALL_OUTPUT.as_posix()}')
        ORDER BY import_value DESC
        LIMIT 10
    """).df().to_string(index=False)
)

# --------------------------------------------------
# 12. PRODUCT HHI
# --------------------------------------------------

print("\nPRODUCT CONCENTRATION SUMMARY")
print("-" * 70)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{HHI_OUTPUT.as_posix()}')
        ORDER BY year
        LIMIT 10
    """).df().to_string(index=False)
)

# --------------------------------------------------
# 13. PRODUCT SHARE GAINERS
# --------------------------------------------------

print("\nBIGGEST PRODUCT SHARE GAINERS: 1988 TO 2020")
print("-" * 70)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{CHANGE_OUTPUT.as_posix()}')
        ORDER BY share_change_percentage_points DESC NULLS LAST
        LIMIT 10
    """).df().to_string(index=False)
)

print("\nBIGGEST PRODUCT SHARE LOSERS: 1988 TO 2020")
print("-" * 70)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{CHANGE_OUTPUT.as_posix()}')
        ORDER BY share_change_percentage_points ASC NULLS LAST
        LIMIT 10
    """).df().to_string(index=False)
)

# --------------------------------------------------
# 14. COMPLETION
# --------------------------------------------------

print("\nOUTPUT FILES")
print("-" * 70)

for file in [
    OVERALL_OUTPUT,
    ANNUAL_OUTPUT,
    HHI_OUTPUT,
    CHANGE_OUTPUT,
    SPECIAL_OUTPUT
]:
    print(file)

print("\n" + "=" * 70)
print(f"Execution time: {time.time() - start:.2f} seconds")
print("PRODUCT TRADE ANALYSIS COMPLETED")
print("=" * 70)

con.close()

