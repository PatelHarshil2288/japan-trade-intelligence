
from pathlib import Path
import duckdb
import time
import sys

PROJECT = Path(r"D:\Japan_Trade_Intelligence")

CSV_FILE = PROJECT / "data" / "raw" / "custom_1988_2020.csv"
OUTPUT_DIR = PROJECT / "data" / "processed" / "parquet"
TEMP_DIR = PROJECT / "temp"
LOG_DIR = PROJECT / "logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "japan_trade.parquet"
LOG_FILE = LOG_DIR / "04_parquet_build.log"

MEMORY_LIMIT = "4GB"
THREADS = 4

def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)

    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(line + "\n")


def main():
    start = time.time()

    log("=" * 65)
    log("JAPAN TRADE INTELLIGENCE - PARQUET WAREHOUSE")
    log("=" * 65)

    if not CSV_FILE.exists():
        raise FileNotFoundError(CSV_FILE)

    if OUTPUT_FILE.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT_FILE}\n"
            "Move or rename it before rebuilding."
        )

    con = duckdb.connect()

    try:
        con.execute(f"SET memory_limit = '{MEMORY_LIMIT}'")
        con.execute(f"SET threads = {THREADS}")
        con.execute(
            f"SET temp_directory = '{TEMP_DIR.as_posix()}'"
        )

        log("DuckDB connected.")
        log(f"Memory limit: {MEMORY_LIMIT}")
        log(f"Threads: {THREADS}")
        log(f"CSV: {CSV_FILE}")
        log(f"Output: {OUTPUT_FILE}")

        csv_path = CSV_FILE.as_posix().replace("'", "''")
        output_path = OUTPUT_FILE.as_posix().replace("'", "''")

        log("Starting CSV to Parquet conversion.")

        query = f"""
        COPY (
            SELECT
                CAST(column0 AS BIGINT) AS ym,
                CAST(column1 AS TINYINT) AS exp_imp,
                CAST(column2 AS VARCHAR) AS Country,
                CAST(column3 AS BIGINT) AS Custom,
                CAST(column4 AS VARCHAR) AS hs9,
                CAST(column5 AS BIGINT) AS Q1,
                CAST(column6 AS BIGINT) AS Q2,
                CAST(column7 AS BIGINT) AS Value,
                CAST(column0 / 100 AS INTEGER) AS year
            FROM read_csv(
                '{csv_path}',
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
        )
        TO '{output_path}'
        (FORMAT PARQUET, COMPRESSION ZSTD);
        """

        con.execute(query)

        log("Parquet conversion completed.")

        log("Validating generated Parquet file.")

        parquet_path = OUTPUT_FILE.as_posix().replace("'", "''")

        validation = con.execute(f"""
            SELECT
                COUNT(*),
                MIN(ym),
                MAX(ym),
                SUM(CASE WHEN exp_imp = 1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN exp_imp = 2 THEN 1 ELSE 0 END),
                SUM(Value)
            FROM read_parquet('{parquet_path}')
        """).fetchone()

        log(f"Parquet row count: {validation[0]:,}")
        log(f"Minimum month: {validation[1]}")
        log(f"Maximum month: {validation[2]}")
        log(f"Export records: {validation[3]:,}")
        log(f"Import records: {validation[4]:,}")
        log(f"Trade value total: {validation[5]:,}")

        if validation[0] != 113_607_322:
            raise RuntimeError("Parquet row count validation FAILED.")

        if validation[1] != 198801 or validation[2] != 202012:
            raise RuntimeError("Parquet date validation FAILED.")

        if validation[3] != 69_088_368:
            raise RuntimeError("Parquet export count validation FAILED.")

        if validation[4] != 44_518_954:
            raise RuntimeError("Parquet import count validation FAILED.")

        if validation[5] != 3_681_820_443_472:
            raise RuntimeError("Parquet trade value validation FAILED.")

        size_gb = OUTPUT_FILE.stat().st_size / (1024 ** 3)
        elapsed = time.time() - start

        log(f"Parquet file size: {size_gb:.3f} GB")
        log(f"Total execution time: {elapsed:.2f} seconds")
        log("OVERALL RESULT: PARQUET VALIDATION PASSED")

    finally:
        con.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        raise
