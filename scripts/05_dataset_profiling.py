
from pathlib import Path
import duckdb
import csv
import time

PROJECT = Path(r"D:\Japan_Trade_Intelligence")

PARQUET_FILE = (
    PROJECT / "data" / "processed" / "parquet"
    / "japan_trade.parquet"
)

OUTPUT_DIR = PROJECT / "data" / "processed" / "aggregated"
LOG_DIR = PROJECT / "logs"
TEMP_DIR = PROJECT / "temp"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "05_dataset_profiling.log"

def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)

    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(line + "\n")


def save_csv(filename, headers, rows):
    output_file = OUTPUT_DIR / filename

    with open(output_file, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    log(f"Saved: {output_file}")


def main():
    start = time.time()

    log("=" * 65)
    log("PHASE 3.1 - DATASET PROFILING")
    log("=" * 65)

    if not PARQUET_FILE.exists():
        raise FileNotFoundError(PARQUET_FILE)

    con = duckdb.connect()

    try:
        con.execute("SET memory_limit = '4GB'")
        con.execute("SET threads = 4")
        con.execute(
            f"SET temp_directory = '{TEMP_DIR.as_posix()}'"
        )

        parquet = PARQUET_FILE.as_posix().replace("'", "''")
        source = f"read_parquet('{parquet}')"

        # 1. Basic dataset information
        log("1. Calculating dataset overview")

        overview = con.execute(f"""
            SELECT
                COUNT(*) AS total_records,
                MIN(ym) AS earliest_month,
                MAX(ym) AS latest_month,
                COUNT(DISTINCT Country) AS unique_countries,
                COUNT(DISTINCT Custom) AS unique_customs,
                COUNT(DISTINCT hs9) AS unique_hs9_products,
                COUNT(DISTINCT exp_imp) AS trade_types,
                SUM(Value) AS total_trade_value,
                MIN(Value) AS minimum_value,
                MAX(Value) AS maximum_value,
                AVG(Value) AS average_value
            FROM {source}
        """).fetchone()

        overview_headers = [
            "total_records",
            "earliest_month",
            "latest_month",
            "unique_countries",
            "unique_customs",
            "unique_hs9_products",
            "trade_types",
            "total_trade_value",
            "minimum_value",
            "maximum_value",
            "average_value"
        ]

        save_csv(
            "01_dataset_overview.csv",
            overview_headers,
            [overview]
        )

        for name, value in zip(overview_headers, overview):
            log(f"{name}: {value}")

        # 2. Column-level profiling
        log("2. Calculating column statistics")

        columns = [
            "ym", "exp_imp", "Country", "Custom",
            "hs9", "Q1", "Q2", "Value", "year"
        ]

        column_rows = []

        for column in columns:
            result = con.execute(f"""
                SELECT
                    COUNT(*) AS total_rows,
                    COUNT("{column}") AS non_null,
                    COUNT(*) - COUNT("{column}") AS null_count,
                    COUNT(DISTINCT "{column}") AS unique_values
                FROM {source}
            """).fetchone()

            column_rows.append([column, *result])

        save_csv(
            "02_column_profile.csv",
            [
                "column_name",
                "total_rows",
                "non_null",
                "null_count",
                "unique_values"
            ],
            column_rows
        )

        # 3. Trade type distribution
        log("3. Analysing import/export distribution")

        trade_rows = con.execute(f"""
            SELECT
                exp_imp,
                COUNT(*) AS record_count,
                SUM(Value) AS total_value,
                AVG(Value) AS average_value,
                MIN(Value) AS minimum_value,
                MAX(Value) AS maximum_value
            FROM {source}
            GROUP BY exp_imp
            ORDER BY exp_imp
        """).fetchall()

        save_csv(
            "03_trade_type_profile.csv",
            [
                "exp_imp",
                "record_count",
                "total_value",
                "average_value",
                "minimum_value",
                "maximum_value"
            ],
            trade_rows
        )

        # 4. Yearly record distribution
        log("4. Analysing yearly record distribution")

        yearly_rows = con.execute(f"""
            SELECT
                year,
                COUNT(*) AS record_count,
                SUM(CASE WHEN exp_imp = 1 THEN 1 ELSE 0 END)
                    AS export_records,
                SUM(CASE WHEN exp_imp = 2 THEN 1 ELSE 0 END)
                    AS import_records,
                SUM(Value) AS total_value
            FROM {source}
            GROUP BY year
            ORDER BY year
        """).fetchall()

        save_csv(
            "04_yearly_record_profile.csv",
            [
                "year",
                "record_count",
                "export_records",
                "import_records",
                "total_value"
            ],
            yearly_rows
        )

        # 5. Quantity statistics
        log("5. Analysing quantity columns")

        quantity_rows = con.execute(f"""
            SELECT
                'Q1' AS column_name,
                COUNT(*) AS total_records,
                COUNT(Q1) AS non_null,
                MIN(Q1) AS minimum,
                MAX(Q1) AS maximum,
                AVG(Q1) AS average,
                SUM(Q1) AS total
            FROM {source}

            UNION ALL

            SELECT
                'Q2',
                COUNT(*),
                COUNT(Q2),
                MIN(Q2),
                MAX(Q2),
                AVG(Q2),
                SUM(Q2)
            FROM {source}
        """).fetchall()

        save_csv(
            "05_quantity_profile.csv",
            [
                "column_name",
                "total_records",
                "non_null",
                "minimum",
                "maximum",
                "average",
                "total"
            ],
            quantity_rows
        )

        log("All profiling reports generated.")

        log(f"Execution time: {time.time() - start:.2f} seconds")
        log("PHASE 3.1 COMPLETED SUCCESSFULLY")

    finally:
        con.close()


if __name__ == "__main__":
    main()
