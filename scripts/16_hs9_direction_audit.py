
from pathlib import Path
import duckdb
import time

ROOT = Path(r"D:\Japan_Trade_Intelligence")

PARQUET_FILE = (
    ROOT / "data" / "processed" / "parquet" / "japan_trade.parquet"
)

OUTPUT_DIR = ROOT / "data" / "processed" / "aggregated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DETAIL_OUTPUT = OUTPUT_DIR / "16_hs9_direction_overlap.csv"
SUMMARY_OUTPUT = OUTPUT_DIR / "16_hs9_direction_summary.csv"

con = duckdb.connect()
con.execute("SET memory_limit = '4GB'")
con.execute("SET threads = 4")
con.execute(
    f"SET temp_directory = '{(ROOT / 'temp').as_posix()}'"
)

start = time.time()

print("=" * 70)
print("HS9 EXPORT / IMPORT CLASSIFICATION AUDIT")
print("=" * 70)

# --------------------------------------------------
# 1. ANALYSE EACH HS9 CODE BY TRADE DIRECTION
# --------------------------------------------------

detail_query = f"""
WITH source_data AS (
    SELECT
        hs9,
        exp_imp,
        Value
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
),

code_summary AS (
    SELECT
        hs9,

        COUNT(*) AS total_records,

        SUM(CASE WHEN exp_imp = 1
                 THEN 1 ELSE 0 END) AS export_records,

        SUM(CASE WHEN exp_imp = 2
                 THEN 1 ELSE 0 END) AS import_records,

        SUM(CASE WHEN exp_imp = 1
                 THEN Value ELSE 0 END) AS export_value,

        SUM(CASE WHEN exp_imp = 2
                 THEN Value ELSE 0 END) AS import_value

    FROM source_data
    GROUP BY hs9
)

SELECT
    hs9 AS hs9_code,
    total_records,
    export_records,
    import_records,
    export_value,
    import_value,

    CASE
        WHEN export_records > 0 AND import_records > 0
            THEN 'Present in both'
        WHEN export_records > 0
            THEN 'Export only'
        WHEN import_records > 0
            THEN 'Import only'
        ELSE 'Other'
    END AS direction_status

FROM code_summary
ORDER BY total_records DESC
"""

con.execute(f"""
COPY ({detail_query})
TO '{DETAIL_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("\nHS9 direction detail saved.")

# --------------------------------------------------
# 2. SUMMARY OF CODE OVERLAP
# --------------------------------------------------

summary_query = f"""
WITH source_data AS (
    SELECT
        hs9,
        exp_imp
    FROM read_parquet('{PARQUET_FILE.as_posix()}')
),

code_summary AS (
    SELECT
        hs9,

        MAX(CASE WHEN exp_imp = 1
                 THEN 1 ELSE 0 END) AS has_export,

        MAX(CASE WHEN exp_imp = 2
                 THEN 1 ELSE 0 END) AS has_import

    FROM source_data
    GROUP BY hs9
)

SELECT
    COUNT(*) AS unique_hs9_codes,

    SUM(CASE
        WHEN has_export = 1 AND has_import = 1
        THEN 1 ELSE 0
    END) AS shared_hs9_codes,

    SUM(CASE
        WHEN has_export = 1 AND has_import = 0
        THEN 1 ELSE 0
    END) AS export_only_hs9_codes,

    SUM(CASE
        WHEN has_export = 0 AND has_import = 1
        THEN 1 ELSE 0
    END) AS import_only_hs9_codes

FROM code_summary
"""

con.execute(f"""
COPY ({summary_query})
TO '{SUMMARY_OUTPUT.as_posix()}'
(HEADER, DELIMITER ',')
""")

print("HS9 direction summary saved.")

# --------------------------------------------------
# 3. VALIDATION AND RESULTS
# --------------------------------------------------

print("\nDIRECTION SUMMARY")
print("-" * 70)

print(
    con.execute(f"""
        SELECT *
        FROM read_csv_auto('{SUMMARY_OUTPUT.as_posix()}')
    """).df().to_string(index=False)
)

print("\nTOP 20 HS9 CODES PRESENT IN BOTH DIRECTIONS")
print("-" * 70)

print(
    con.execute(f"""
        SELECT
            hs9_code,
            export_records,
            import_records,
            export_value,
            import_value,
            direction_status
        FROM read_csv_auto('{DETAIL_OUTPUT.as_posix()}')
        WHERE direction_status = 'Present in both'
        ORDER BY total_records DESC
        LIMIT 20
    """).df().to_string(index=False)
)

print("\nOUTPUT FILES")
print("-" * 70)
print(DETAIL_OUTPUT)
print(SUMMARY_OUTPUT)

print("\n" + "=" * 70)
print(f"Execution time: {time.time() - start:.2f} seconds")
print("HS9 CLASSIFICATION AUDIT COMPLETED")
print("=" * 70)

con.close()

