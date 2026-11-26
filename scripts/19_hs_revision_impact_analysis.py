
from pathlib import Path
import time
import duckdb
import pandas as pd

# ============================================================
# JAPAN TRADE INTELLIGENCE
# PHASE 5.4 — HS REVISION IMPACT ANALYSIS
# ============================================================

START_TIME = time.time()

PROJECT_DIR = Path(r"D:\Japan_Trade_Intelligence")
PARQUET_FILE = (
    PROJECT_DIR / "data" / "processed" / "parquet"
    / "japan_trade.parquet"
)
OUTPUT_DIR = (
    PROJECT_DIR / "data" / "processed" / "aggregated"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REVISION_YEARS = [1992, 1996, 2002, 2007, 2012, 2017]

SPECIAL_CODES = [
    "000000019",
    "000000099",
    "000000190"
]

if not PARQUET_FILE.exists():
    raise FileNotFoundError(f"Parquet file not found: {PARQUET_FILE}")

print("=" * 75)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 5.4 — HS REVISION IMPACT ANALYSIS")
print("=" * 75)

con = duckdb.connect()
con.execute("SET memory_limit = '4GB'")
con.execute("SET threads = 4")
con.execute(
    "SET temp_directory = 'D:/Japan_Trade_Intelligence/temp'"
)

parquet_path = str(PARQUET_FILE).replace("\\", "/")

special_sql = ", ".join(f"'{code}'" for code in SPECIAL_CODES)

# ------------------------------------------------------------
# 1. Retrieve annual distinct HS6 code sets
# ------------------------------------------------------------

print("\n[1/4] Reading annual HS6 code sets...")

annual_data = con.execute(f"""
    SELECT DISTINCT
        CAST(ym // 100 AS INTEGER) AS year,
        LEFT(CAST(hs9 AS VARCHAR), 6) AS hs6_code
    FROM read_parquet('{parquet_path}')
    WHERE CAST(hs9 AS VARCHAR) NOT IN ({special_sql})
      AND exp_imp IN (1, 2)
      AND ym BETWEEN 198801 AND 202012
    ORDER BY year, hs6_code
""").df()

con.close()

annual_sets = {}

for year, group in annual_data.groupby("year"):
    annual_sets[int(year)] = set(group["hs6_code"].astype(str))

years = sorted(annual_sets.keys())

if years != list(range(1988, 2021)):
    raise ValueError(
        "Unexpected year coverage. Expected 1988 through 2020."
    )

print(f"Years covered: {len(years)}")
print(f"Annual code observations: {len(annual_data):,}")

# ------------------------------------------------------------
# 2. Calculate annual entries and exits
# ------------------------------------------------------------

print("[2/4] Calculating annual entries and exits...")

annual_metrics = []
revision_code_details = []

for year in years:

    current_codes = annual_sets[year]
    current_count = len(current_codes)

    if year == 1988:
        previous_codes = set()
        new_codes = current_codes.copy()
        exited_codes = set()
        previous_count = 0
        is_baseline = True
    else:
        previous_codes = annual_sets[year - 1]
        previous_count = len(previous_codes)

        new_codes = current_codes - previous_codes
        exited_codes = previous_codes - current_codes
        is_baseline = False

    new_count = len(new_codes)
    exited_count = len(exited_codes)

    new_rate = (
        100 * new_count / current_count
        if current_count else 0
    )

    exit_rate = (
        100 * exited_count / previous_count
        if previous_count else 0
    )

    combined_turnover_rate = (
        100 * (new_count + exited_count)
        / (current_count + previous_count)
        if current_count + previous_count else 0
    )

    is_revision_year = year in REVISION_YEARS

    annual_metrics.append({
        "year": year,
        "is_revision_year": is_revision_year,
        "active_hs6_codes": current_count,
        "previous_year_codes": previous_count,
        "new_codes": new_count,
        "exited_codes": exited_count,
        "net_code_change": new_count - exited_count,
        "new_code_rate_pct": round(new_rate, 2),
        "exit_code_rate_pct": round(exit_rate, 2),
        "combined_turnover_rate_pct": round(
            combined_turnover_rate, 2
        ),
        "is_1988_baseline": is_baseline
    })

    if is_revision_year:
        for code in sorted(new_codes):
            revision_code_details.append({
                "revision_year": year,
                "hs6_code": code,
                "change_type": "Newly observed"
            })

        for code in sorted(exited_codes):
            revision_code_details.append({
                "revision_year": year,
                "hs6_code": code,
                "change_type": "No longer observed"
            })

annual_df = pd.DataFrame(annual_metrics)

annual_df.to_csv(
    OUTPUT_DIR / "19_annual_hs6_transition_metrics.csv",
    index=False
)

# ------------------------------------------------------------
# 3. Revision years versus non-revision years
# ------------------------------------------------------------

print("[3/4] Comparing revision and non-revision years...")

comparison_rows = []

for year in REVISION_YEARS:

    row = annual_df.loc[annual_df["year"] == year].iloc[0]

    comparison_rows.append({
        "revision_year": year,
        "previous_year_codes": int(row["previous_year_codes"]),
        "active_hs6_codes": int(row["active_hs6_codes"]),
        "new_codes": int(row["new_codes"]),
        "exited_codes": int(row["exited_codes"]),
        "net_code_change": int(row["net_code_change"]),
        "new_code_rate_pct": row["new_code_rate_pct"],
        "exit_code_rate_pct": row["exit_code_rate_pct"],
        "combined_turnover_rate_pct":
            row["combined_turnover_rate_pct"]
    })

revision_df = pd.DataFrame(comparison_rows)

# Exclude 1988 because it is the first observed year.
non_revision_df = annual_df[
    (~annual_df["is_revision_year"])
    & (~annual_df["is_1988_baseline"])
].copy()

comparison_summary = pd.DataFrame([
    {
        "year_group": "Revision years",
        "number_of_years": len(revision_df),
        "average_new_codes": round(
            revision_df["new_codes"].mean(), 2
        ),
        "average_exited_codes": round(
            revision_df["exited_codes"].mean(), 2
        ),
        "average_turnover_rate_pct": round(
            revision_df["combined_turnover_rate_pct"].mean(), 2
        ),
        "median_turnover_rate_pct": round(
            revision_df["combined_turnover_rate_pct"].median(), 2
        )
    },
    {
        "year_group": "Non-revision years",
        "number_of_years": len(non_revision_df),
        "average_new_codes": round(
            non_revision_df["new_codes"].mean(), 2
        ),
        "average_exited_codes": round(
            non_revision_df["exited_codes"].mean(), 2
        ),
        "average_turnover_rate_pct": round(
            non_revision_df["combined_turnover_rate_pct"].mean(), 2
        ),
        "median_turnover_rate_pct": round(
            non_revision_df["combined_turnover_rate_pct"].median(), 2
        )
    }
])

revision_df.to_csv(
    OUTPUT_DIR / "19_hs_revision_year_comparison.csv",
    index=False
)

comparison_summary.to_csv(
    OUTPUT_DIR / "19_revision_vs_nonrevision_summary.csv",
    index=False
)

# ------------------------------------------------------------
# 4. Export exact codes entering or exiting in revision years
# ------------------------------------------------------------

print("[4/4] Exporting revision-year code lists...")

revision_codes_df = pd.DataFrame(
    revision_code_details,
    columns=["revision_year", "hs6_code", "change_type"]
)

revision_codes_df.to_csv(
    OUTPUT_DIR / "19_revision_year_code_changes.csv",
    index=False
)

# ------------------------------------------------------------
# VALIDATION
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("VALIDATION")
print("-" * 75)

print(f"Total unique HS6 codes: {annual_data['hs6_code'].nunique():,}")
print(f"Annual observations: {len(annual_data):,}")
print(f"Revision years checked: {len(REVISION_YEARS)}")
print(f"Revision code changes exported: {len(revision_codes_df):,}")

print("\nREVISION YEAR COMPARISON")
print("-" * 75)
print(revision_df.to_string(index=False))

print("\nREVISION VS NON-REVISION SUMMARY")
print("-" * 75)
print(comparison_summary.to_string(index=False))

print("\nALL REVISION YEARS — ANNUAL METRICS")
print("-" * 75)

print(
    annual_df[annual_df["is_revision_year"]][
        [
            "year",
            "active_hs6_codes",
            "new_codes",
            "exited_codes",
            "net_code_change",
            "combined_turnover_rate_pct"
        ]
    ].to_string(index=False)
)

print("\nOUTPUT FILES")
print("-" * 75)

output_files = [
    "19_annual_hs6_transition_metrics.csv",
    "19_hs_revision_year_comparison.csv",
    "19_revision_vs_nonrevision_summary.csv",
    "19_revision_year_code_changes.csv"
]

for filename in output_files:
    print(OUTPUT_DIR / filename)

print("\n" + "=" * 75)
print(f"Execution time: {time.time() - START_TIME:.2f} seconds")
print("HS REVISION IMPACT ANALYSIS COMPLETED")
print("=" * 75)
