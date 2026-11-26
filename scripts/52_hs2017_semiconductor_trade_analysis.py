
from pathlib import Path
import duckdb

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"
PARQUET = ROOT / "data" / "processed" / "parquet" / "japan_trade.parquet"

OUT_ANNUAL = AGG / "52_hs2017_semiconductor_annual_trade.csv"
OUT_MONTHLY = AGG / "52_hs2017_semiconductor_monthly_trade.csv"
OUT_PARTNERS = AGG / "52_hs2017_semiconductor_partner_trade.csv"
OUT_HS9 = AGG / "52_hs2017_semiconductor_hs9_detail.csv"
OUT_SUMMARY = AGG / "52_hs2017_semiconductor_trade_summary.txt"

def main():
    if not PARQUET.exists():
        raise FileNotFoundError(PARQUET)

    AGG.mkdir(parents=True, exist_ok=True)

    # Normalize Windows path for SQL.
    parquet_path = str(PARQUET).replace("\\", "/")
    parquet_path_sql = parquet_path.replace("'", "''")

    con = duckdb.connect()

    con.execute(f"""
        CREATE VIEW trade AS
        SELECT
            TRY_CAST(ym AS INTEGER) AS ym,
            TRY_CAST(exp_imp AS INTEGER) AS exp_imp,
            CAST(Country AS VARCHAR) AS country,
            LPAD(
                REGEXP_REPLACE(
                    TRIM(CAST(hs9 AS VARCHAR)),
                    '\\\\.0$',
                    ''
                ),
                9,
                '0'
            ) AS hs9,
            TRY_CAST(Value AS DOUBLE) AS value
        FROM read_parquet('{parquet_path_sql}')
    """)

    # HS2017 classification period in this project: 2017-2020.
    # Use only direct HS9 records whose first six digits match
    # the three target HS2017 codes.
    con.execute("""
        CREATE VIEW semiconductor_trade AS
        SELECT
            CAST(SUBSTR(CAST(ym AS VARCHAR), 1, 4) AS INTEGER) AS year,
            ym,
            exp_imp,
            CASE
                WHEN exp_imp = 1 THEN 'Export'
                WHEN exp_imp = 2 THEN 'Import'
                ELSE 'Unknown'
            END AS trade_direction,
            country,
            hs9,
            SUBSTR(hs9, 1, 6) AS hs6,
            value
        FROM trade
        WHERE ym BETWEEN 201701 AND 202012
          AND exp_imp IN (1, 2)
          AND value IS NOT NULL
          AND LENGTH(hs9) = 9
          AND SUBSTR(hs9, 1, 6) IN (
              '854231', '854232', '854239'
          )
    """)

    annual = con.execute("""
        SELECT
            year,
            hs6,
            trade_direction,
            COUNT(*) AS record_count,
            SUM(value) AS value_thousand_yen
        FROM semiconductor_trade
        GROUP BY year, hs6, trade_direction
        ORDER BY year, hs6, trade_direction
    """).df()

    monthly = con.execute("""
        SELECT
            ym,
            hs6,
            trade_direction,
            COUNT(*) AS record_count,
            SUM(value) AS value_thousand_yen
        FROM semiconductor_trade
        GROUP BY ym, hs6, trade_direction
        ORDER BY ym, hs6, trade_direction
    """).df()

    partners = con.execute("""
        SELECT
            year,
            hs6,
            trade_direction,
            country,
            COUNT(*) AS record_count,
            SUM(value) AS value_thousand_yen
        FROM semiconductor_trade
        GROUP BY year, hs6, trade_direction, country
        ORDER BY year, hs6, trade_direction,
                 value_thousand_yen DESC
    """).df()

    hs9_detail = con.execute("""
        SELECT
            hs6,
            hs9,
            trade_direction,
            COUNT(*) AS record_count,
            SUM(value) AS value_thousand_yen
        FROM semiconductor_trade
        GROUP BY hs6, hs9, trade_direction
        ORDER BY hs6, trade_direction, value_thousand_yen DESC
    """).df()

    annual.to_csv(OUT_ANNUAL, index=False)
    monthly.to_csv(OUT_MONTHLY, index=False)
    partners.to_csv(OUT_PARTNERS, index=False)
    hs9_detail.to_csv(OUT_HS9, index=False)

    totals = con.execute("""
        SELECT
            hs6,
            trade_direction,
            COUNT(*) AS record_count,
            SUM(value) AS value_thousand_yen,
            MIN(ym) AS first_month,
            MAX(ym) AS last_month,
            COUNT(DISTINCT country) AS partner_count,
            COUNT(DISTINCT hs9) AS hs9_code_count
        FROM semiconductor_trade
        GROUP BY hs6, trade_direction
        ORDER BY hs6, trade_direction
    """).df()

    lines = [
        "PHASE 52 — DIRECT HS2017 SEMICONDUCTOR TRADE",
        "Period: 2017-01 through 2020-12",
        "Basis: direct HS9 records, first six digits match HS2017 targets",
        "Values are in thousand yen.",
        "",
        "Summary by HS6 and trade direction:",
    ]

    if totals.empty:
        lines.append("No matching records found.")
    else:
        for _, row in totals.iterrows():
            lines.append(
                f"{row['hs6']} | {row['trade_direction']} | "
                f"records={int(row['record_count']):,} | "
                f"value={row['value_thousand_yen']:,.0f} thousand yen | "
                f"partners={int(row['partner_count']):,} | "
                f"HS9 codes={int(row['hs9_code_count']):,} | "
                f"period={row['first_month']}-{row['last_month']}"
            )

    lines += [
        "",
        "Caution:",
        "These are directly classified records for 2017-2020 only.",
        "Do not interpret this as a complete 1988-2020 historical series.",
        "Do not use HS2012 ex mappings to allocate trade values.",
        "",
        f"Annual output: {OUT_ANNUAL}",
        f"Monthly output: {OUT_MONTHLY}",
        f"Partner output: {OUT_PARTNERS}",
        f"HS9 detail output: {OUT_HS9}",
    ]

    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    print("\nPhase 52 completed.")
    print("Annual:", OUT_ANNUAL)
    print("Monthly:", OUT_MONTHLY)
    print("Partners:", OUT_PARTNERS)
    print("HS9 detail:", OUT_HS9)
    print("Summary:", OUT_SUMMARY)
    print("\n".join(lines))

    con.close()

if __name__ == "__main__":
    main()

