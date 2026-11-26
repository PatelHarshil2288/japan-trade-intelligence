
from pathlib import Path
import sqlite3
import duckdb
import json
import time

PROJECT = Path(r"D:\Japan_Trade_Intelligence")

CSV_PATH = PROJECT / "data/raw/custom_1988_2020.csv"
DB_PATH = PROJECT / "data/raw/custom_1988_2020.db"
TEMP_PATH = PROJECT / "temp"

TEMP_PATH.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 1 - DATA INTEGRITY VALIDATION")
print("=" * 65)

# ------------------------------------------
# 1. SQLITE AGGREGATES
# ------------------------------------------

print("\n[1] ANALYSING SQLITE")

db = sqlite3.connect(
    DB_PATH.resolve().as_uri() + "?mode=ro",
    uri=True
)

query = """
SELECT
    COUNT(*) AS total_records,
    MIN(ym) AS earliest_month,
    MAX(ym) AS latest_month,

    SUM(CASE WHEN exp_imp = 1 THEN 1 ELSE 0 END)
        AS export_records,

    SUM(CASE WHEN exp_imp = 2 THEN 1 ELSE 0 END)
        AS import_records,

    SUM(CASE WHEN exp_imp NOT IN (1,2)
             THEN 1 ELSE 0 END)
        AS other_trade_records,

    SUM(CAST(Q1 AS REAL)) AS total_q1,
    SUM(CAST(Q2 AS REAL)) AS total_q2,
    SUM(CAST(Value AS REAL)) AS total_value,

    SUM(CASE WHEN ym IS NULL THEN 1 ELSE 0 END)
        AS null_ym,

    SUM(CASE WHEN Country IS NULL THEN 1 ELSE 0 END)
        AS null_country,

    SUM(CASE WHEN hs9 IS NULL THEN 1 ELSE 0 END)
        AS null_hs9,

    SUM(CASE WHEN Value IS NULL THEN 1 ELSE 0 END)
        AS null_value

FROM custom_1988_2020
"""

start = time.time()
sqlite_result = db.execute(query).fetchone()
sqlite_time = time.time() - start

db.close()

# ------------------------------------------
# 2. DUCKDB CSV AGGREGATES
# ------------------------------------------

print("[2] ANALYSING CSV")

con = duckdb.connect()

con.execute("SET memory_limit = '4GB'")
con.execute("SET threads = 4")
con.execute("SET preserve_insertion_order = false")

con.execute(
    f"SET temp_directory = '{TEMP_PATH.as_posix()}'"
)

csv_file = CSV_PATH.as_posix().replace("'", "''")

csv_query = f"""
SELECT
    COUNT(*) AS total_records,

    MIN(TRY_CAST(column0 AS INTEGER))
        AS earliest_month,

    MAX(TRY_CAST(column0 AS INTEGER))
        AS latest_month,

    SUM(CASE WHEN TRY_CAST(column1 AS INTEGER) = 1
             THEN 1 ELSE 0 END)
        AS export_records,

    SUM(CASE WHEN TRY_CAST(column1 AS INTEGER) = 2
             THEN 1 ELSE 0 END)
        AS import_records,

    SUM(CASE WHEN TRY_CAST(column1 AS INTEGER)
                  NOT IN (1,2)
             THEN 1 ELSE 0 END)
        AS other_trade_records,

    SUM(TRY_CAST(column5 AS DOUBLE)) AS total_q1,
    SUM(TRY_CAST(column6 AS DOUBLE)) AS total_q2,
    SUM(TRY_CAST(column7 AS DOUBLE)) AS total_value,

    COUNT(*) FILTER (WHERE column0 IS NULL)
        AS null_ym,

    COUNT(*) FILTER (WHERE column2 IS NULL)
        AS null_country,

    COUNT(*) FILTER (WHERE column4 IS NULL)
        AS null_hs9,

    COUNT(*) FILTER (WHERE column7 IS NULL)
        AS null_value

FROM read_csv(
    '{csv_file}',
    header = false,
    auto_detect = false,
    columns = {{
        'column0': 'BIGINT',
        'column1': 'BIGINT',
        'column2': 'VARCHAR',
        'column3': 'BIGINT',
        'column4': 'VARCHAR',
        'column5': 'BIGINT',
        'column6': 'BIGINT',
        'column7': 'BIGINT'
    }}
)
"""

start = time.time()
csv_result = con.execute(csv_query).fetchone()
csv_time = time.time() - start

# ------------------------------------------
# 3. COMPARE RESULTS
# ------------------------------------------

labels = [
    "Total records",
    "Earliest month",
    "Latest month",
    "Export records",
    "Import records",
    "Other trade records",
    "Total Q1",
    "Total Q2",
    "Total trade value",
    "NULL ym",
    "NULL Country",
    "NULL hs9",
    "NULL Value"
]

print("\n[3] COMPARISON REPORT")

all_passed = True

for label, sql_value, csv_value in zip(
    labels, sqlite_result, csv_result
):

    if label in ["Total Q1", "Total Q2", "Total trade value"]:
        passed = abs(float(sql_value or 0) -
                      float(csv_value or 0)) <= max(
                          1.0,
                          abs(float(sql_value or 0)) * 1e-9
                      )
    else:
        passed = sql_value == csv_value

    status = "PASS" if passed else "CHECK"

    if not passed:
        all_passed = False

    print(f"\n{label}")
    print("SQLite:", sql_value)
    print("CSV:   ", csv_value)
    print("Status:", status)

print("\nSQLITE TIME:", round(sqlite_time, 2), "seconds")
print("CSV TIME:", round(csv_time, 2), "seconds")

print("\nOVERALL RESULT:",
      "AGGREGATES MATCH" if all_passed
      else "DIFFERENCES REQUIRE INVESTIGATION")

con.close()

print("\nVALIDATION FINISHED")
