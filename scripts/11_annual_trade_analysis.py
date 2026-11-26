
from pathlib import Path
import duckdb
import csv
import time

PROJECT = Path(r"D:\Japan_Trade_Intelligence")

PARQUET = (
    PROJECT / "data" / "processed" / "parquet"
    / "japan_trade.parquet"
)

OUTPUT = PROJECT / "data" / "processed" / "aggregated"
LOG = PROJECT / "logs" / "11_annual_trade_analysis.log"
TEMP = PROJECT / "temp"

SPECIAL_CODES = (
    "'000000019'",
    "'000000099'",
    "'000000190'"
)


def log(message):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)

    with open(LOG, "a", encoding="utf-8") as file:
        file.write(line + "\n")


def save_csv(filename, headers, rows):
    path = OUTPUT / filename

    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    log(f"Saved: {path}")


def main():
    start = time.time()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    TEMP.mkdir(parents=True, exist_ok=True)

    log("=" * 65)
    log("PHASE 3.3 - ANNUAL TRADE INTELLIGENCE")
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

        parquet = PARQUET.as_posix().replace("'", "''")
        source = f"read_parquet('{parquet}')"

        special_list = ", ".join(SPECIAL_CODES)

        # Full customs trade, including special categories
        log("1. Calculating full customs trade by year")

        full_query = f"""
            SELECT
                year,
                COUNT(*) AS total_records,

                SUM(CASE WHEN exp_imp = 1 THEN Value ELSE 0 END)
                    AS export_value,

                SUM(CASE WHEN exp_imp = 2 THEN Value ELSE 0 END)
                    AS import_value,

                SUM(Value) AS total_trade_value,

                SUM(CASE WHEN exp_imp = 1 THEN 1 ELSE 0 END)
                    AS export_records,

                SUM(CASE WHEN exp_imp = 2 THEN 1 ELSE 0 END)
                    AS import_records

            FROM {source}
            GROUP BY year
            ORDER BY year
        """

        full = con.execute(full_query).fetchall()

        # Ordinary merchandise excludes the three confirmed special codes
        log("2. Calculating ordinary merchandise trade")

        ordinary_query = f"""
            SELECT
                year,
                COUNT(*) AS total_records,

                SUM(CASE WHEN exp_imp = 1 THEN Value ELSE 0 END)
                    AS export_value,

                SUM(CASE WHEN exp_imp = 2 THEN Value ELSE 0 END)
                    AS import_value,

                SUM(Value) AS total_trade_value

            FROM {source}
            WHERE hs9 NOT IN ({special_list})
            GROUP BY year
            ORDER BY year
        """

        ordinary = con.execute(ordinary_query).fetchall()

        # Special categories
        log("3. Calculating special customs category totals")

        special_query = f"""
            SELECT
                year,
                hs9,
                exp_imp,
                COUNT(*) AS records,
                SUM(Value) AS total_value
            FROM {source}
            WHERE hs9 IN ({special_list})
            GROUP BY year, hs9, exp_imp
            ORDER BY year, hs9, exp_imp
        """

        special = con.execute(special_query).fetchall()

        # Build yearly report
        log("4. Calculating trade balance and annual growth")

        ordinary_lookup = {
            row[0]: row for row in ordinary
        }

        report_rows = []
        previous_export = None
        previous_import = None
        previous_total = None

        for row in full:
            (
                year,
                records,
                exports,
                imports,
                total,
                export_records,
                import_records
            ) = row

            ordinary_row = ordinary_lookup[year]

            ordinary_records = ordinary_row[1]
            ordinary_exports = ordinary_row[2]
            ordinary_imports = ordinary_row[3]
            ordinary_total = ordinary_row[4]

            balance = exports - imports
            ordinary_balance = ordinary_exports - ordinary_imports

            export_growth = (
                (exports / previous_export - 1) * 100
                if previous_export else None
            )

            import_growth = (
                (imports / previous_import - 1) * 100
                if previous_import else None
            )

            total_growth = (
                (total / previous_total - 1) * 100
                if previous_total else None
            )

            report_rows.append([
                year,
                records,
                exports,
                imports,
                total,
                balance,
                export_records,
                import_records,
                ordinary_records,
                ordinary_exports,
                ordinary_imports,
                ordinary_total,
                ordinary_balance,
                export_growth,
                import_growth,
                total_growth
            ])

            previous_export = exports
            previous_import = imports
            previous_total = total

        headers = [
            "year",
            "full_trade_records",
            "full_export_value",
            "full_import_value",
            "full_total_trade_value",
            "full_trade_balance",
            "export_records",
            "import_records",
            "ordinary_trade_records",
            "ordinary_export_value",
            "ordinary_import_value",
            "ordinary_total_trade_value",
            "ordinary_trade_balance",
            "export_yoy_growth_pct",
            "import_yoy_growth_pct",
            "total_trade_yoy_growth_pct"
        ]

        save_csv(
            "11_annual_trade_intelligence.csv",
            headers,
            report_rows
        )

        save_csv(
            "11_special_categories_annual.csv",
            [
                "year",
                "hs9",
                "exp_imp",
                "records",
                "total_value"
            ],
            special
        )

        # Summary checks
        log("5. Validating annual totals")

        full_total = sum(row[4] for row in full)
        ordinary_total = sum(row[4] for row in ordinary)

        log(f"Full trade value: {full_total:,}")
        log(f"Ordinary trade value: {ordinary_total:,}")
        log(f"Special category value: {full_total - ordinary_total:,}")

        log(f"Years analysed: {len(full)}")

        log(f"Execution time: {time.time() - start:.2f} seconds")
        log("PHASE 3.3 COMPLETED")

    finally:
        con.close()


if __name__ == "__main__":
    main()
