
from pathlib import Path
import duckdb

PROJECT = Path(r"D:\Japan_Trade_Intelligence")
PARQUET = PROJECT / "data/processed/parquet/japan_trade.parquet"
OUTPUT = PROJECT / "data/processed/aggregated"

con = duckdb.connect()
con.execute("SET memory_limit = '4GB'")
con.execute("SET threads = 4")

source = f"read_parquet('{PARQUET.as_posix()}')"

queries = {
    "Q1_zero_by_trade_type": f"""
        SELECT exp_imp, COUNT(*) AS records
        FROM {source}
        WHERE Q1 = 0
        GROUP BY exp_imp ORDER BY exp_imp
    """,
    "Q2_zero_by_trade_type": f"""
        SELECT exp_imp, COUNT(*) AS records
        FROM {source}
        WHERE Q2 = 0
        GROUP BY exp_imp ORDER BY exp_imp
    """,
    "Q1_Q2_zero_combinations": f"""
        SELECT
            CASE
                WHEN Q1 = 0 AND Q2 = 0 THEN 'Both zero'
                WHEN Q1 = 0 THEN 'Q1 only zero'
                WHEN Q2 = 0 THEN 'Q2 only zero'
                ELSE 'Neither zero'
            END AS quantity_pattern,
            COUNT(*) AS records
        FROM {source}
        GROUP BY quantity_pattern
        ORDER BY records DESC
    """,
    "Q1_Q2_by_year": f"""
        SELECT
            year,
            COUNT(*) AS records,
            SUM(CASE WHEN Q1 = 0 THEN 1 ELSE 0 END) AS q1_zero,
            SUM(CASE WHEN Q2 = 0 THEN 1 ELSE 0 END) AS q2_zero
        FROM {source}
        GROUP BY year
        ORDER BY year
    """
}

try:
    for name, query in queries.items():
        print(f"\n{'=' * 65}\n{name}\n{'=' * 65}")

        result = con.execute(query).fetchdf()
        result.to_csv(
            OUTPUT / f"07_{name}.csv",
            index=False,
            encoding="utf-8-sig"
        )
        print(result.to_string(index=False))

finally:
    con.close()
