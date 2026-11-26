
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT = AGG / "60_semiconductor_country_hs6_contribution.csv"

OUTPUT_MATRIX = AGG / "61_semiconductor_hs6_contribution_matrix.csv"
OUTPUT_SUMMARY = AGG / "61_semiconductor_hs6_contribution_matrix_summary.txt"

HS6_CODES = ["854231", "854232", "854239"]

print("=" * 72)
print("PHASE 61 â€” HS6 CONTRIBUTION MATRIX")
print("=" * 72)

if not INPUT.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT}")

df = pd.read_csv(INPUT, low_memory=False)

required = [
    "country_code",
    "country_name",
    "trade_direction",
    "hs6",
    "value_2017_thousand_yen",
    "value_2020_thousand_yen",
    "value_change_thousand_yen",
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["hs6"] = df["hs6"].astype(str).str.strip().str.zfill(6)
df["country_code"] = (
    df["country_code"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.strip()
    .str.zfill(3)
)

for col in [
    "value_2017_thousand_yen",
    "value_2020_thousand_yen",
    "value_change_thousand_yen",
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

if df[
    [
        "value_2017_thousand_yen",
        "value_2020_thousand_yen",
        "value_change_thousand_yen",
    ]
].isna().any().any():
    raise ValueError("Missing or non-numeric values found.")

if not set(df["hs6"]).issubset(set(HS6_CODES)):
    unexpected = sorted(set(df["hs6"]) - set(HS6_CODES))
    raise ValueError(f"Unexpected HS6 codes: {unexpected}")

# Aggregate each country/direction/HS6 in case there are repeated rows.
keys = ["country_code", "country_name", "trade_direction", "hs6"]

base = (
    df.groupby(keys, as_index=False)
    .agg(
        value_2017_thousand_yen=("value_2017_thousand_yen", "sum"),
        value_2020_thousand_yen=("value_2020_thousand_yen", "sum"),
        value_change_thousand_yen=("value_change_thousand_yen", "sum"),
    )
)

# Create one row per country and direction.
index_cols = ["country_code", "country_name", "trade_direction"]

matrix = base.pivot_table(
    index=index_cols,
    columns="hs6",
    values="value_change_thousand_yen",
    aggfunc="sum",
    fill_value=0,
).reset_index()

matrix.columns.name = None

# Ensure all expected HS6 columns exist.
for hs6 in HS6_CODES:
    if hs6 not in matrix.columns:
        matrix[hs6] = 0

# Rename columns clearly.
matrix = matrix.rename(
    columns={
        "854231": "change_854231_thousand_yen",
        "854232": "change_854232_thousand_yen",
        "854239": "change_854239_thousand_yen",
    }
)

change_cols = [
    "change_854231_thousand_yen",
    "change_854232_thousand_yen",
    "change_854239_thousand_yen",
]

matrix["total_change_thousand_yen"] = matrix[change_cols].sum(axis=1)

matrix["change_854231_trillion_yen"] = (
    matrix["change_854231_thousand_yen"] / 1_000_000_000
)
matrix["change_854232_trillion_yen"] = (
    matrix["change_854232_thousand_yen"] / 1_000_000_000
)
matrix["change_854239_trillion_yen"] = (
    matrix["change_854239_thousand_yen"] / 1_000_000_000
)
matrix["total_change_trillion_yen"] = (
    matrix["total_change_thousand_yen"] / 1_000_000_000
)

# Check that the matrix total matches the original country-direction totals.
original_totals = (
    base.groupby(index_cols, as_index=False)
    .agg(original_change_thousand_yen=("value_change_thousand_yen", "sum"))
)

matrix = matrix.merge(original_totals, on=index_cols, how="left")

matrix["reconciliation_difference_thousand_yen"] = (
    matrix["total_change_thousand_yen"] -
    matrix["original_change_thousand_yen"]
)

if not (
    matrix["reconciliation_difference_thousand_yen"].abs() < 0.01
).all():
    raise ValueError("Matrix reconciliation failed.")

matrix["largest_absolute_hs6_driver"] = matrix[change_cols].abs().idxmax(axis=1)
matrix["largest_absolute_hs6_driver"] = (
    matrix["largest_absolute_hs6_driver"]
    .str.extract(r"change_(\d{6})")[0]
)

matrix = matrix.sort_values(
    ["trade_direction", "total_change_trillion_yen"],
    ascending=[True, False],
)

matrix.to_csv(OUTPUT_MATRIX, index=False, encoding="utf-8-sig")

# Summary by trade direction and HS6 code.
summary_lines = [
    "PHASE 61 - HS6 CONTRIBUTION MATRIX",
    "=" * 68,
    "Period: 2017 vs 2020",
    "Scope: HS6 854231, 854232, 854239",
    "Values: trillion yen",
    "",
    "TOTAL CHANGE BY HS6 AND TRADE DIRECTION",
    "-" * 68,
]

hs6_summary = (
    base.groupby(["trade_direction", "hs6"], as_index=False)
    .agg(change_thousand_yen=("value_change_thousand_yen", "sum"))
)

hs6_summary["change_trillion_yen"] = (
    hs6_summary["change_thousand_yen"] / 1_000_000_000
)

for _, row in hs6_summary.sort_values(
    ["trade_direction", "hs6"]
).iterrows():
    summary_lines.append(
        f"{row['trade_direction']} | HS6 {row['hs6']} | "
        f"Change: {row['change_trillion_yen']:+.6f} T yen"
    )

for direction in ["Export", "Import"]:
    summary_lines.extend([
        "",
        f"TOP COUNTRY NET INCREASES - {direction.upper()}",
        "-" * 68,
    ])

    subset = matrix[matrix["trade_direction"] == direction]
    for _, row in subset.nlargest(
        10, "total_change_trillion_yen"
    ).iterrows():
        summary_lines.append(
            f"{row['country_name']} ({row['country_code']}) | "
            f"Total: {row['total_change_trillion_yen']:+.6f} T yen | "
            f"854231: {row['change_854231_trillion_yen']:+.6f} | "
            f"854232: {row['change_854232_trillion_yen']:+.6f} | "
            f"854239: {row['change_854239_trillion_yen']:+.6f}"
        )

    summary_lines.extend([
        "",
        f"TOP COUNTRY NET DECREASES - {direction.upper()}",
        "-" * 68,
    ])

    for _, row in subset.nsmallest(
        10, "total_change_trillion_yen"
    ).iterrows():
        summary_lines.append(
            f"{row['country_name']} ({row['country_code']}) | "
            f"Total: {row['total_change_trillion_yen']:+.6f} T yen | "
            f"854231: {row['change_854231_trillion_yen']:+.6f} | "
            f"854232: {row['change_854232_trillion_yen']:+.6f} | "
            f"854239: {row['change_854239_trillion_yen']:+.6f}"
        )

OUTPUT_SUMMARY.write_text(
    "\n".join(summary_lines),
    encoding="utf-8",
)

print(f"\nMatrix rows: {len(matrix):,}")
print(f"Matrix saved: {OUTPUT_MATRIX.name}")
print(f"Summary saved: {OUTPUT_SUMMARY.name}")
print(
    "Maximum reconciliation difference: "
    f"{matrix['reconciliation_difference_thousand_yen'].abs().max():,.6f}"
    " thousand yen"
)
print("\nPhase 61 completed successfully.")

