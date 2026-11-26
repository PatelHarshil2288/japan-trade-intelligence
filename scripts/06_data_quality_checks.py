
from pathlib import Path
import duckdb
import time

PROJECT = Path(r"D:\Japan_Trade_Intelligence")

PARQUET = (
    PROJECT / "data" / "processed" / "parquet"
    / "japan_trade.parquet"
)

OUTPUT = (
    PROJECT / "data" / "processed" / "aggregated"
    / "06_data_quality_report.csv"
)

LOG = PROJECT / "logs" / "06_data_quality_checks.log"
TEMP = PROJECT / "temp"


def log(message):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)

    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    start = time.time()

    log("=" * 65)
    log("PHASE 3.2 - DATA QUALITY INVESTIGATION")
    log("=" * 65)

    if not PARQUET.exists():
        raise FileNotFoundError(PARQUET)

    con = duckdb.connect()

    try:
        con.execute("SET memory_limit = '4GB'")
        con.execute("SET threads = 4")
        con.execute(
            f"SET temp_directory = '{TEMP.as_posix()}'"
        )

        path = PARQUET.as_posix().replace("'", "''")
        source = f"read_parquet('{path}')"

        checks = []

        def add_check(name, query):
            result = con.execute(query).fetchone()[0]
            checks.append((name, int(result)))
            log(f"{name}: {result:,}")

        log("Running basic validity checks...")

        add_check(
            "Invalid_month_values",
            f"""
            SELECT COUNT(*) FROM {source}
            WHERE ym % 100 NOT BETWEEN 1 AND 12
            OR (ym // 100) NOT BETWEEN 1988 AND 2020
            """
        )

        add_check(
            "Invalid_trade_type_codes",
            f"""
            SELECT COUNT(*) FROM {source}
            WHERE exp_imp NOT IN (1, 2)
            """
        )

        add_check(
            "Zero_Q1_records",
            f"SELECT COUNT(*) FROM {source} WHERE Q1 = 0"
        )

        add_check(
            "Negative_Q1_records",
            f"SELECT COUNT(*) FROM {source} WHERE Q1 < 0"
        )

        add_check(
            "Zero_Q2_records",
            f"SELECT COUNT(*) FROM {source} WHERE Q2 = 0"
        )

        add_check(
            "Negative_Q2_records",
            f"SELECT COUNT(*) FROM {source} WHERE Q2 < 0"
        )

        add_check(
            "Zero_trade_value_records",
            f"SELECT COUNT(*) FROM {source} WHERE Value = 0"
        )

        add_check(
            "Negative_trade_value_records",
            f"SELECT COUNT(*) FROM {source} WHERE Value < 0"
        )

        add_check(
            "Invalid_HS9_length",
            f"""
            SELECT COUNT(*) FROM {source}
            WHERE hs9 IS NULL
               OR LENGTH(TRIM(hs9)) != 9
            """
        )

        add_check(
            "Non_numeric_HS9_codes",
            f"""
            SELECT COUNT(*) FROM {source}
            WHERE NOT REGEXP_MATCHES(hs9, '^[0-9]+$')
            """
        )

        log("Checking exact duplicate records...")
        log("This operation may take several minutes.")

        add_check(
            "Duplicate_excess_records",
            f"""
            SELECT COUNT(*) - COUNT(DISTINCT (
                ym, exp_imp, Country, Custom,
                hs9, Q1, Q2, Value
            ))
            FROM {source}
            """
        )

        OUTPUT.parent.mkdir(parents=True, exist_ok=True)

        with open(OUTPUT, "w", encoding="utf-8-sig") as f:
            f.write("check_name,record_count\n")
            for name, count in checks:
                f.write(f"{name},{count}\n")

        log(f"Report saved: {OUTPUT}")
        log(f"Execution time: {time.time() - start:.2f} seconds")
        log("PHASE 3.2 CHECKS COMPLETED")

    finally:
        con.close()


if __name__ == "__main__":
    main()
