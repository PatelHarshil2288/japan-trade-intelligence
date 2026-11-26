
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

RANKINGS_OUTPUT = OUTPUT_DIR / "14_annual_partner_rankings.csv"
TOP5_OUTPUT = OUTPUT_DIR / "14_top5_partners_by_year.csv"
CONCENTRATION_OUTPUT = OUTPUT_DIR / "14_annual_partner_concentration.csv"
CHANGE_OUTPUT = OUTPUT_DIR / "14_partner_change_1988_2020.csv"

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
print("COUNTRY PARTNER EVOLUTION AND DEPENDENCY ANALYSIS")
print("=" * 70)

# --------------------------------------------------
# 3. ANNUAL PARTNER RANKINGS AND MARKET SHARES
# --------------------------------------------------

rankings_query = f"""
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

        COUNT(*) AS total_records,

        SUM(CASE WHEN exp_imp = 1
                 THEN Value ELSE 0 END) AS export_value,

        SUM(CASE WHEN exp_imp = 2
                 THEN Value ELSE 0 END) AS import_value,

        SUM(Value) AS total_trade_value

    FROM source_data
    GROUP BY year, Country
),

shares AS (
    SELECT
        *,
        SUM(total_trade_value) OVER (PARTITION BY year)
            AS year_total_trade,

        SUM(export_value) OVER (PARTITION BY year)
            AS year_total_exports,

        SUM(import_value) OVER (PARTITION BY year)
            AS year_total_imports

    FROM annual_country
),

ranked AS (
    SELECT
        year,
        CAST(Country AS VARCHAR) AS country_code,
        total_records,
        export_value,
        import_value,
        total_trade_value,

        export_value - import_value AS trade_balance,

        100.0 * total_trade_value /
            NULLIF(year_total_trade, 0) AS total_trade_share_pct,

        100.0 * export_value /
            NULLIF(year_total_exports, 0) AS export_share_pct,

        100.0 * import_value /
            NULLIF(year_total_imports, 0) AS import_share_pct,

        ROW_NUMBER() OVER (
            PARTITION BY year
            ORDER BY total_trade_value DESC, Country
        ) AS total_trade_rank,

        ROW_NUMBER() OVER (
            PARTITION BY year
            ORDER BY export_value DESC, Country
        ) AS export_rank,

        ROW_NUMBER() OVER (
            PARTITION BY year
            ORDER BY import_value DESC, Country
        ) AS import_rank

    FROM shares
)

SELECT *
FROM ranked
ORDER BY year, total_trade_rank
"""

con.execute(f"""
COPY ({rankings_query})
TO '{RANKINGS_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("\nAnnual partner rankings saved.")

# --------------------------------------------------
# 4. TOP FIVE PARTNERS BY YEAR
# --------------------------------------------------

con.execute(f"""
COPY (
    SELECT *
    FROM read_csv_auto('{RANKINGS_OUTPUT.as_posix()}')
    WHERE total_trade_rank <= 5
    ORDER BY year, total_trade_rank
)
TO '{TOP5_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Top-five partner analysis saved.")

# --------------------------------------------------
# 5. ANNUAL PARTNER CONCENTRATION
# --------------------------------------------------

concentration_query = f"""
WITH rankings AS (
    SELECT *
    FROM read_csv_auto('{RANKINGS_OUTPUT.as_posix()}')
)

SELECT
    year,

    COUNT(*) AS partner_count,

    ROUND(SUM(
        CASE WHEN total_trade_rank <= 2
             THEN total_trade_share_pct ELSE 0 END
    ), 4) AS top2_total_trade_share_pct,

    ROUND(SUM(
        CASE WHEN total_trade_rank <= 5
             THEN total_trade_share_pct ELSE 0 END
    ), 4) AS top5_total_trade_share_pct,

    ROUND(SUM(
        CASE WHEN export_rank <= 5
             THEN export_share_pct ELSE 0 END
    ), 4) AS top5_export_share_pct,

    ROUND(SUM(
        CASE WHEN import_rank <= 5
             THEN import_share_pct ELSE 0 END
    ), 4) AS top5_import_share_pct

FROM rankings
GROUP BY year
ORDER BY year
"""

con.execute(f"""
COPY ({concentration_query})
TO '{CONCENTRATION_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("Annual partner concentration saved.")

# --------------------------------------------------
# 6. COMPARE 1988 WITH 2020
# --------------------------------------------------

change_query = f"""
WITH rankings AS (
    SELECT *
    FROM read_csv_auto('{RANKINGS_OUTPUT.as_posix()}')
),

start_year AS (
    SELECT
        country_code,
        total_trade_value AS trade_value_1988,
        total_trade_share_pct AS trade_share_1988,
        export_share_pct AS export_share_1988,
        import_share_pct AS import_share_1988,
        total_trade_rank AS trade_rank_1988
    FROM rankings
    WHERE year = 1988
),

end_year AS (
    SELECT
        country_code,
        total_trade_value AS trade_value_2020,
        total_trade_share_pct AS trade_share_2020,
        export_share_pct AS export_share_2020,
        import_share_pct AS import_share_2020,
        total_trade_rank AS trade_rank_2020
    FROM rankings
    WHERE year = 2020
)

SELECT
    COALESCE(s.country_code, e.country_code) AS country_code,

    s.trade_value_1988,
    e.trade_value_2020,

    s.trade_share_1988,
    e.trade_share_2020,

    e.trade_share_2020 - s.trade_share_1988
        AS trade_share_change_percentage_points,

    s.export_share_1988,
    e.export_share_2020,

    s.import_share_1988,
    e.import_share_2020,

    s.trade_rank_1988,
    e.trade_rank_2020,

    CASE
        WHEN s.trade_rank_1988 IS NULL THEN 'New in 2020'
        WHEN e.trade_rank_2020 IS NULL THEN 'Not present in 2020'
        ELSE 'Present in both years'
    END AS presence_status

FROM start_year s
FULL OUTER JOIN end_year e
    ON s.country_code = e.country_code

ORDER BY
    trade_share_change_percentage_points DESC NULLS LAST
"""

con.execute(f"""
COPY ({change_query})
TO '{CHANGE_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("1988 versus 2020 comparison saved.")

# --------------------------------------------------
# 7. VALIDATION
# --------------------------------------------------

rankings_count = con.execute(f"""
    SELECT COUNT(*)
    FROM read_csv_auto('{RANKINGS_OUTPUT.as_posix()}')
""").fetchone()[0]

top5_count = con.execute(f"""
    SELECT COUNT(*)
    FROM read_csv_auto('{TOP5_OUTPUT.as_posix()}')
""").fetchone()[0]

concentration_count = con.execute(f"""
    SELECT COUNT(*)
    FROM read_csv_auto('{CONCENTRATION_OUTPUT.as_posix()}')
""").fetchone()[0]

change_count = con.execute(f"""
    SELECT COUNT(*)
    FROM read_csv_auto('{CHANGE_OUTPUT.as_posix()}')
""").fetchone()[0]

print("\nVALIDATION")
print("-" * 70)
print(f"Annual partner observations: {rankings_count}")
print(f"Top-five observations: {top5_count}")
print(f"Annual concentration observations: {concentration_count}")
print(f"1988-2020 comparison partner codes: {change_count}")

print("\nTOP FIVE PARTNERS IN 1988")
print("-" * 70)

print(
    con.execute(f"""
        SELECT
            country_code,
            total_trade_value,
            total_trade_share_pct,
            total_trade_rank
        FROM read_csv_auto('{RANKINGS_OUTPUT.as_posix()}')
        WHERE year = 1988
          AND total_trade_rank <= 5
        ORDER BY total_trade_rank
    """).df().to_string(index=False)
)

print("\nTOP FIVE PARTNERS IN 2020")
print("-" * 70)

print(
    con.execute(f"""
        SELECT
            country_code,
            total_trade_value,
            total_trade_share_pct,
            total_trade_rank
        FROM read_csv_auto('{RANKINGS_OUTPUT.as_posix()}')
        WHERE year = 2020
          AND total_trade_rank <= 5
        ORDER BY total_trade_rank
    """).df().to_string(index=False)
)

print("\nTOP FIVE CONCENTRATION YEARS")
print("-" * 70)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{CONCENTRATION_OUTPUT.as_posix()}')
        ORDER BY top5_total_trade_share_pct DESC
        LIMIT 5
    """).df().to_string(index=False)
)

print("\nLOWEST FIVE CONCENTRATION YEARS")
print("-" * 70)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{CONCENTRATION_OUTPUT.as_posix()}')
        ORDER BY top5_total_trade_share_pct
        LIMIT 5
    """).df().to_string(index=False)
)

print("\nBIGGEST PARTNER SHARE GAINERS: 1988 TO 2020")
print("-" * 70)

print(
    con.execute(f"""
        SELECT
            country_code,
            trade_share_1988,
            trade_share_2020,
            trade_share_change_percentage_points,
            trade_rank_1988,
            trade_rank_2020,
            presence_status
        FROM read_csv_auto('{CHANGE_OUTPUT.as_posix()}')
        ORDER BY trade_share_change_percentage_points DESC NULLS LAST
        LIMIT 10
    """).df().to_string(index=False)
)

print("\nBIGGEST PARTNER SHARE LOSERS: 1988 TO 2020")
print("-" * 70)

print(
    con.execute(f"""
        SELECT
            country_code,
            trade_share_1988,
            trade_share_2020,
            trade_share_change_percentage_points,
            trade_rank_1988,
            trade_rank_2020,
            presence_status
        FROM read_csv_auto('{CHANGE_OUTPUT.as_posix()}')
        ORDER BY trade_share_change_percentage_points ASC NULLS LAST
        LIMIT 10
    """).df().to_string(index=False)
)

print("\n" + "=" * 70)
print(f"Execution time: {time.time() - start:.2f} seconds")
print("PARTNER EVOLUTION ANALYSIS COMPLETED")
print("=" * 70)

con.close()
