
from pathlib import Path
import os
import sqlite3
import duckdb

# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

PROJECT = Path(r"D:\Japan_Trade_Intelligence")

CSV_PATH = PROJECT / "data" / "raw" / "custom_1988_2020.csv"
DB_PATH = PROJECT / "data" / "raw" / "custom_1988_2020.db"

TEMP_PATH = PROJECT / "temp"
TEMP_PATH.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 1 - DATASET INSPECTION")
print("=" * 65)

# ==========================================
# 2. ENVIRONMENT INFORMATION
# ==========================================

print("\n[1] ENVIRONMENT")

print("Python:", os.sys.version.split()[0])
print("DuckDB:", duckdb.__version__)

# ==========================================
# 3. FILE VALIDATION
# ==========================================

print("\n[2] FILE VALIDATION")

for file in [CSV_PATH, DB_PATH]:

    if file.exists():
        size_gb = file.stat().st_size / (1024 ** 3)

        print(f"\nFile: {file.name}")
        print(f"Size: {size_gb:.3f} GB")
        print("Status: AVAILABLE")

    else:
        print(f"\nMISSING: {file}")

if not CSV_PATH.exists():
    raise FileNotFoundError(CSV_PATH)

# ==========================================
# 4. DATABASE SIGNATURE
# ==========================================

print("\n[3] DATABASE IDENTIFICATION")

if DB_PATH.exists():

    with open(DB_PATH, "rb") as f:
        signature = f.read(16)

    print("File signature:", repr(signature))

    if signature.startswith(b"SQLite format 3"):

        print("Database type: SQLite")

        try:
            uri = DB_PATH.resolve().as_uri() + "?mode=ro"

            db = sqlite3.connect(uri, uri=True)

            tables = db.execute("""
                SELECT name, type
                FROM sqlite_master
                WHERE type IN ('table', 'view')
            """).fetchall()

            print("Tables and views:")

            for table in tables:
                print(table)

            db.close()

        except Exception as error:
            print("SQLite inspection error:", error)

    elif signature.startswith(b"DUCK"):

        print("Possible DuckDB database signature.")

    else:
        print("Database format not yet identified.")
        print("We will investigate it separately.")

# ==========================================
# 5. CSV INSPECTION
# ==========================================

print("\n[4] CSV SCHEMA INSPECTION")

con = duckdb.connect()

con.execute("SET memory_limit = '4GB'")
con.execute("SET threads = 4")
con.execute("SET preserve_insertion_order = false")

con.execute(
    f"SET temp_directory = '{TEMP_PATH.as_posix()}'"
)

csv_file = CSV_PATH.as_posix().replace("'", "''")

schema = con.execute(f"""
    DESCRIBE
    SELECT *
    FROM read_csv_auto(
        '{csv_file}',
        sample_size = 20000
    )
""").fetchdf()

print(schema.to_string(index=False))

print("\nTotal detected columns:", len(schema))

# ==========================================
# 6. FIRST 10 RECORDS
# ==========================================

print("\n[5] FIRST 10 RECORDS")

sample = con.execute(f"""
    SELECT *
    FROM read_csv_auto(
        '{csv_file}',
        sample_size = 20000
    )
    LIMIT 10
""").fetchdf()

print(sample.to_string(index=False))

# ==========================================
# 7. BASIC CSV METADATA
# ==========================================

print("\n[6] CSV METADATA")

print("CSV filename:", CSV_PATH.name)
print("CSV size in GB:",
      round(CSV_PATH.stat().st_size / (1024 ** 3), 3))

print("\nFull row count and date range are deferred")
print("to the next controlled scanning step.")

# ==========================================
# 8. CLOSE CONNECTION
# ==========================================

con.close()

print("\n" + "=" * 65)
print("INITIAL INSPECTION COMPLETED SUCCESSFULLY")
print("=" * 65)
