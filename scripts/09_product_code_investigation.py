
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

    # 1. Special and zero-prefixed HS9 codes
    print("\n1. ZERO-PREFIX HS9 CODES")

    special = con.execute(f"""
        SELECT
            hs9,
            COUNT(*) AS records,
            SUM(Value) AS total_value,
            SUM(CASE WHEN Q1 = 0 THEN 1 ELSE 0 END) AS q1_zero,
            SUM(CASE WHEN Q2 = 0 THEN 1 ELSE 0 END) AS q2_zero
        FROM {source}
        WHERE LEFT(hs9, 1) = '0'
        GROUP BY hs9
        ORDER BY records DESC
    """).fetchdf()

    special.to_csv(
        OUTPUT / "09_special_hs9_codes.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print(special.head(30).to_string(index=False))

    # 2. Top products by total trade value
    print("\n2. TOP 20 PRODUCTS BY TRADE VALUE")

    top_products = con.execute(f"""
        SELECT
            hs9,
            COUNT(*) AS records,
            SUM(Value) AS total_value,
            SUM(CASE WHEN exp_imp = 1 THEN Value ELSE 0 END)
                AS export_value,
            SUM(CASE WHEN exp_imp = 2 THEN Value ELSE 0 END)
                AS import_value
        FROM {source}
        GROUP BY hs9
        ORDER BY total_value DESC
        LIMIT 20
    """).fetchdf()

    top_products.to_csv(
        OUTPUT / "09_top_products_by_value.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print(top_products.to_string(index=False))

    # 3. Country codes
    print("\n3. COUNTRY CODE DISTRIBUTION")

    countries = con.execute(f"""
        SELECT
            Country,
            COUNT(*) AS records,
            SUM(Value) AS total_value
        FROM {source}
        GROUP BY Country
        ORDER BY total_value DESC
        LIMIT 30
    """).fetchdf()

    countries.to_csv(
        OUTPUT / "09_top_country_codes.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print(countries.to_string(index=False))

finally:
    con.close()
