
from pathlib import Path
import sqlite3
import duckdb
import time

# ==========================================
# PROJECT PATHS
# ==========================================

PROJECT = Path(r"D:\Japan_Trade_Intelligence")

CSV_PATH = PROJECT / "data" / "raw" / "custom_1988_2020.csv"
DB_PATH = PROJECT / "data" / "raw" / "custom_1988_2020.db"
TEMP_PATH = PROJECT / "temp"

TEMP_PATH.mkdir(parents=True, exist_ok=True)

# ==========================================
# START
# ==========================================

print("=" * 65)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 1 - RECORD VERIFICATION")
print("=" * 65)

# ==========================================
# PART A: SQLITE INSPECTION
# ==========================================

print("\n[A] SQLITE DATABASE INSPECTION")

if not DB_PATH.exists():
    raise FileNotFoundError(DB_PATH)

uri = DB_PATH.resolve().as_uri() + "?mode=ro"

db = sqlite3.connect(uri, uri=True)

tables = db.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
""").fetchall()

print("Tables:", tables)

table_name = "custom_1988_2020"

if not any(row[0] == table_name for row in tables):
    raise RuntimeError("Expected SQLite table not found.")

print("\nSQLite column information:")

columns = db.execute(
    f'PRAGMA table_info("{table_name}")'
).fetchall()

for col in columns:
    print(col)

print("\nCounting SQLite records...")

start = time.time()

sqlite_result = db.execute(
    f'SELECT COUNT(*) FROM "{table_name}"'
).fetchone()

sqlite_count = sqlite_result[0]

print("SQLite total records:", f"{sqlite_count:,}")
print("SQLite counting time:", round(time.time() - start, 2), "seconds")

print("\nSQLite sample:")

sample = db.execute(
    f'SELECT * FROM "{table_name}" LIMIT 5'
).fetchall()

for row in sample:
    print(row)

db.close()

# ==========================================
# PART B: CSV INSPECTION
# ==========================================

print("\n[B] CSV FULL RECORD COUNT")

if not CSV_PATH.exists():
    raise FileNotFoundError(CSV_PATH)

con = duckdb.connect()

con.execute("SET memory_limit = '4GB'")
con.execute("SET threads = 4")
con.execute("SET preserve_insertion_order = false")

con.execute(
    f"SET temp_directory = '{TEMP_PATH.as_posix()}'"
)

csv_file = CSV_PATH.as_posix().replace("'", "''")

print("Starting full CSV scan...")
print("This may take several minutes.")

start = time.time()

csv_result = con.execute(f"""
    SELECT
        COUNT(*) AS total_records,
        MIN(TRY_CAST(column0 AS INTEGER)) AS earliest_month,
        MAX(TRY_CAST(column0 AS INTEGER)) AS latest_month
    FROM read_csv_auto(
        '{csv_file}',
        header = false,
        sample_size = 20000
    )
""").fetchone()

csv_time = time.time() - start

csv_count = csv_result[0]

print("\nCSV RESULTS")
print("Total records:", f"{csv_count:,}")
print("Earliest month:", csv_result[1])
print("Latest month:", csv_result[2])
print("Scanning time:", round(csv_time, 2), "seconds")

# ==========================================
# PART C: COMPARISON
# ==========================================

print("\n[C] DATASET COMPARISON")

print("CSV records:", f"{csv_count:,}")
print("SQLite records:", f"{sqlite_count:,}")

if csv_count == sqlite_count:
    print("RESULT: Record counts match.")
else:
    print("RESULT: Record counts differ.")
    print("Further investigation required.")

print("\nCSV scan time:", round(csv_time, 2), "seconds")

con.close()

print("\n" + "=" * 65)
print("RECORD VERIFICATION COMPLETED")
print("=" * 65)
