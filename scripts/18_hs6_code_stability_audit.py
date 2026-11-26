
from pathlib import Path
import time
import duckdb

# ============================================================
# JAPAN TRADE INTELLIGENCE
# PHASE 5.3 — HS6 CODE STABILITY AUDIT
# ============================================================

START_TIME = time.time()

PROJECT_DIR = Path(r"D:\Japan_Trade_Intelligence")
PARQUET_FILE = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "parquet"
    / "japan_trade.parquet"
)
OUTPUT_DIR = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "aggregated"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not PARQUET_FILE.exists():
    raise FileNotFoundError(f"Parquet file not found: {PARQUET_FILE}")

print("=" * 75)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 5.3 — HS6 CODE STABILITY AUDIT")
print("=" * 75)

con = duckdb.connect()
con.execute("SET memory_limit = '4GB'")
con.execute("SET threads = 4")
con.execute("SET temp_directory = 'D:/Japan_Trade_Intelligence/temp'")

parquet_path = str(PARQUET_FILE).replace("\\", "/").replace("'", "''")

# Exclude the three previously identified special customs codes.
SPECIAL_CODES = ("000000019", "000000099", "000000190")

con.execute(f"""
    CREATE TEMP VIEW trade_source AS
    SELECT
        CAST(ym // 100 AS INTEGER) AS year,
        CAST(exp_imp AS INTEGER) AS exp_imp,
        CAST(hs9 AS VARCHAR) AS hs9_code,
        LEFT(CAST(hs9 AS VARCHAR), 6) AS hs6_code,
        CAST(Value AS BIGINT) AS trade_value
    FROM read_parquet('{parquet_path}')
    WHERE CAST(hs9 AS VARCHAR) NOT IN {SPECIAL_CODES}
      AND exp_imp IN (1, 2)
      AND ym BETWEEN 198801 AND 202012
""")

# ------------------------------------------------------------
# 1. HS6 code activity by year
# ------------------------------------------------------------

print("\n[1/5] Building annual HS6 code activity...")

annual_activity = con.execute("""
    SELECT
        year,
        hs6_code,
        COUNT(*) AS record_count,
        SUM(trade_value) AS total_trade_value,
        SUM(CASE WHEN exp_imp = 1 THEN trade_value ELSE 0 END)
            AS export_value,
        SUM(CASE WHEN exp_imp = 2 THEN trade_value ELSE 0 END)
            AS import_value,
        MAX(CASE WHEN exp_imp = 1 THEN 1 ELSE 0 END)
            AS appears_in_exports,
        MAX(CASE WHEN exp_imp = 2 THEN 1 ELSE 0 END)
            AS appears_in_imports
    FROM trade_source
    GROUP BY year, hs6_code
    ORDER BY year, hs6_code
""").df()

annual_activity.to_csv(
    OUTPUT_DIR / "18_hs6_annual_code_activity.csv",
    index=False
)

# ------------------------------------------------------------
# 2. Code-level continuity across the full period
# ------------------------------------------------------------

print("[2/5] Measuring code continuity...")

code_stability = con.execute("""
    WITH annual_codes AS (
        SELECT
            year,
            hs6_code,
            MAX(CASE WHEN exp_imp = 1 THEN 1 ELSE 0 END)
                AS has_export,
            MAX(CASE WHEN exp_imp = 2 THEN 1 ELSE 0 END)
                AS has_import
        FROM trade_source
        GROUP BY year, hs6_code
    )
    SELECT
        hs6_code,
        COUNT(*) AS active_years,
        MIN(year) AS first_active_year,
        MAX(year) AS last_active_year,
        SUM(has_export) AS export_active_years,
        SUM(has_import) AS import_active_years,
        CASE
            WHEN COUNT(*) = 33 THEN 'Full period: 33 years'
            WHEN COUNT(*) >= 25 THEN 'Long duration: 25-32 years'
            WHEN COUNT(*) >= 10 THEN 'Medium duration: 10-24 years'
            ELSE 'Short duration: 1-9 years'
        END AS continuity_group
    FROM annual_codes
    GROUP BY hs6_code
    ORDER BY active_years DESC, hs6_code
""").df()

code_stability.to_csv(
    OUTPUT_DIR / "18_hs6_code_stability.csv",
    index=False
)

# ------------------------------------------------------------
# 3. Annual code counts and apparent entries/exits
# ------------------------------------------------------------

print("[3/5] Identifying annual code entries and exits...")

annual_transitions = con.execute("""
    WITH annual_codes AS (
        SELECT DISTINCT year, hs6_code
        FROM trade_source
    ),
    years AS (
        SELECT DISTINCT year
        FROM trade_source
    ),
    annual_counts AS (
        SELECT
            year,
            COUNT(*) AS active_hs6_codes
        FROM annual_codes
        GROUP BY year
    ),
    transitions AS (
        SELECT
            y.year,
            COUNT(DISTINCT CASE
                WHEN current_code.hs6_code IS NOT NULL
                 AND previous_code.hs6_code IS NULL
                THEN current_code.hs6_code
            END) AS apparent_new_codes,
            COUNT(DISTINCT CASE
                WHEN previous_code.hs6_code IS NOT NULL
                 AND current_code.hs6_code IS NULL
                THEN previous_code.hs6_code
            END) AS apparent_disappeared_codes
        FROM years y
        LEFT JOIN annual_codes current_code
            ON current_code.year = y.year
        LEFT JOIN annual_codes previous_code
            ON previous_code.year = y.year - 1
           AND previous_code.hs6_code = current_code.hs6_code
        GROUP BY y.year
    ),
    exits AS (
        SELECT
            y.year,
            COUNT(DISTINCT CASE
                WHEN previous_code.hs6_code IS NOT NULL
                AND current_code.hs6_code IS NULL
                THEN previous_code.hs6_code
            END) AS apparent_exited_codes
        FROM years y
        LEFT JOIN annual_codes previous_code
            ON previous_code.year = y.year - 1
        LEFT JOIN annual_codes current_code
            ON current_code.year = y.year
        AND current_code.hs6_code = previous_code.hs6_code
        GROUP BY y.year
    )
    SELECT
        a.year,
        a.active_hs6_codes,
        COALESCE(t.apparent_new_codes, 0) AS apparent_new_codes,
        COALESCE(e.apparent_exited_codes, 0) AS apparent_exited_codes
    FROM annual_counts a
    LEFT JOIN transitions t USING (year)
    LEFT JOIN exits e USING (year)
    ORDER BY a.year
""").df()

annual_transitions.to_csv(
    OUTPUT_DIR / "18_hs6_annual_entries_exits.csv",
    index=False
)

# ------------------------------------------------------------
# 4. Export/import direction stability by HS6
# ------------------------------------------------------------

print("[4/5] Checking export/import direction continuity...")

direction_stability = con.execute("""
    WITH annual_direction AS (
        SELECT
            year,
            hs6_code,
            MAX(CASE WHEN exp_imp = 1 THEN 1 ELSE 0 END)
                AS has_export,
            MAX(CASE WHEN exp_imp = 2 THEN 1 ELSE 0 END)
                AS has_import
        FROM trade_source
        GROUP BY year, hs6_code
    )
    SELECT
        hs6_code,
        COUNT(*) AS active_years,
        SUM(has_export) AS export_active_years,
        SUM(has_import) AS import_active_years,
        CASE
            WHEN SUM(has_export) > 0 AND SUM(has_import) > 0
                THEN 'Both directions'
            WHEN SUM(has_export) > 0
                THEN 'Export only'
            ELSE 'Import only'
        END AS observed_direction_group
    FROM annual_direction
    GROUP BY hs6_code
    ORDER BY active_years DESC, hs6_code
""").df()

direction_stability.to_csv(
    OUTPUT_DIR / "18_hs6_direction_stability.csv",
    index=False
)

# ------------------------------------------------------------
# 5. Continuity group summary
# ------------------------------------------------------------

print("[5/5] Creating continuity summary...")

continuity_summary = con.execute("""
    WITH annual_codes AS (
        SELECT
            hs6_code,
            COUNT(DISTINCT year) AS active_years
        FROM trade_source
        GROUP BY hs6_code
    )
    SELECT
        CASE
            WHEN active_years = 33 THEN 'Full period: 33 years'
            WHEN active_years >= 25 THEN 'Long duration: 25-32 years'
            WHEN active_years >= 10 THEN 'Medium duration: 10-24 years'
            ELSE 'Short duration: 1-9 years'
        END AS continuity_group,
        COUNT(*) AS hs6_code_count,
        ROUND(
            100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
            2
        ) AS share_of_codes_pct
    FROM annual_codes
    GROUP BY continuity_group
    ORDER BY
        CASE continuity_group
            WHEN 'Full period: 33 years' THEN 1
            WHEN 'Long duration: 25-32 years' THEN 2
            WHEN 'Medium duration: 10-24 years' THEN 3
            ELSE 4
        END
""").df()

continuity_summary.to_csv(
    OUTPUT_DIR / "18_hs6_continuity_summary.csv",
    index=False
)

# ------------------------------------------------------------
# VALIDATION AND CONSOLE SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("VALIDATION")
print("-" * 75)

print(f"Unique HS6 codes: {len(code_stability):,}")
print(f"Annual HS6 code observations: {len(annual_activity):,}")
print(f"Annual transition observations: {len(annual_transitions):,}")
print(f"Direction stability observations: {len(direction_stability):,}")

print("\nCONTINUITY GROUP SUMMARY")
print("-" * 75)
print(continuity_summary.to_string(index=False))

print("\nMOST PERSISTENT HS6 CODES")
print("-" * 75)
print(
    code_stability.head(15)[
        [
            "hs6_code",
            "active_years",
            "first_active_year",
            "last_active_year",
            "continuity_group"
        ]
    ].to_string(index=False)
)

print("\nLEAST PERSISTENT HS6 CODES")
print("-" * 75)
print(
    code_stability.tail(15)[
        [
            "hs6_code",
            "active_years",
            "first_active_year",
            "last_active_year",
            "continuity_group"
        ]
    ].to_string(index=False)
)

print("\nANNUAL CODE COUNTS — FIRST 10 YEARS")
print("-" * 75)
print(annual_transitions.head(10).to_string(index=False))

print("\nANNUAL CODE COUNTS — LAST 10 YEARS")
print("-" * 75)
print(annual_transitions.tail(10).to_string(index=False))

print("\nOUTPUT FILES")
print("-" * 75)

output_files = [
    "18_hs6_annual_code_activity.csv",
    "18_hs6_code_stability.csv",
    "18_hs6_annual_entries_exits.csv",
    "18_hs6_direction_stability.csv",
    "18_hs6_continuity_summary.csv",
]

for filename in output_files:
    print(OUTPUT_DIR / filename)

con.close()

print("\n" + "=" * 75)
print(f"Execution time: {time.time() - START_TIME:.2f} seconds")
print("HS6 CODE STABILITY AUDIT COMPLETED")
print("=" * 75)
