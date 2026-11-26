
from pathlib import Path
import duckdb

PROJECT = Path(r"D:\Japan_Trade_Intelligence")
PARQUET = PROJECT / "data/processed/parquet/japan_trade.parquet"
OUTPUT = PROJECT / "data/processed/aggregated"

con = duckdb.connect()

try:
    con.execute("SET memory_limit = '4GB'")
    con.execute("SET threads = 4")

    source = f"read_parquet('{PARQUET.as_posix()}')"

    print("\nSPECIAL CUSTOMS CATEGORIES")

    query = f"""
        SELECT
            hs9,
            CASE
                WHEN hs9 = '000000190'
                    THEN 'Re-exported goods - other'
                WHEN hs9 = '000000099'
                    THEN 'Re-imported goods - other'
                WHEN hs9 = '000000019'
                    THEN 'Stores - other'
                ELSE 'Other zero-prefixed code'
            END AS category,
            exp_imp,
            year,
            COUNT(*) AS records,
            SUM(Value) AS total_value
        FROM {source}
        WHERE hs9 IN (
            '000000190',
            '000000099',
            '000000019'
        )
        GROUP BY hs9, category, exp_imp, year
        ORDER BY hs9, year, exp_imp
    """

    result = con.execute(query).fetchdf()

    result.to_csv(
        OUTPUT / "10_special_trade_categories.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print(result.head(40).to_string(index=False))

    print("\nTOTALS BY SPECIAL CATEGORY")

    summary = con.execute(f"""
        SELECT
            hs9,
            exp_imp,
            COUNT(*) AS records,
            SUM(Value) AS total_value
        FROM {source}
        WHERE hs9 IN (
            '000000190',
            '000000099',
            '000000019'
        )
        GROUP BY hs9, exp_imp
        ORDER BY hs9, exp_imp
    """).fetchdf()

    print(summary.to_string(index=False))

finally:
    con.close()
