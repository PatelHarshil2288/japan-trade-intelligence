
from pathlib import Path
import duckdb

PROJECT = Path(r"D:\Japan_Trade_Intelligence")

PARQUET = PROJECT / "data/processed/parquet/japan_trade.parquet"
OUTPUT = PROJECT / "data/processed/aggregated"

con = duckdb.connect()

try:
    con.execute("SET memory_limit = '4GB'")
    con.execute("SET threads = 4")
    con.execute(
        f"SET temp_directory = '{(PROJECT / 'temp').as_posix()}'"
    )

    source = f"read_parquet('{PARQUET.as_posix()}')"

    print("\n1. QUANTITY PATTERNS BY HS9 PRODUCT")

    query = f"""
        SELECT
            hs9,
            COUNT(*) AS records,
            SUM(CASE WHEN Q1 = 0 THEN 1 ELSE 0 END) AS q1_zero,
            SUM(CASE WHEN Q2 = 0 THEN 1 ELSE 0 END) AS q2_zero,
            SUM(CASE WHEN Q1 = 0 AND Q2 = 0 THEN 1 ELSE 0 END)
                AS both_zero,
            SUM(Value) AS total_value
        FROM {source}
        GROUP BY hs9
        ORDER BY records DESC
    """

    result = con.execute(query).fetchdf()

    result.to_csv(
        OUTPUT / "08_quantity_by_product.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print(result.head(20).to_string(index=False))

    print("\n2. PRODUCTS WITH BOTH QUANTITIES ZERO")

    both_zero = result[result["both_zero"] > 0].sort_values(
        "both_zero", ascending=False
    )

    print(both_zero.head(20).to_string(index=False))

    print("\n3. REPORT SAVED")
    print(OUTPUT / "08_quantity_by_product.csv")

finally:
    con.close()
