
from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# PHASE 58 — Semiconductor Partner Shift Analysis
# Compare 2017 vs 2020 for HS6 854231, 854232, 854239
# ============================================================

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT_FILE = AGG / "57_semiconductor_partner_full_enriched.csv"

OUTPUT_FULL = AGG / "58_semiconductor_partner_shift_full.csv"
OUTPUT_GAINERS = AGG / "58_semiconductor_partner_value_gainers.csv"
OUTPUT_LOSERS = AGG / "58_semiconductor_partner_value_losers.csv"
OUTPUT_SHARE_UP = AGG / "58_semiconductor_partner_share_increases.csv"
OUTPUT_SHARE_DOWN = AGG / "58_semiconductor_partner_share_decreases.csv"
OUTPUT_SUMMARY = AGG / "58_semiconductor_partner_shift_summary.txt"

REQUIRED_COLUMNS = [
    "hs6",
    "trade_direction",
    "country",
    "value_2017_thousand_yen",
    "value_2020_thousand_yen",
    "value_change_thousand_yen",
    "value_change_trillion_yen",
    "share_2017_pct",
    "share_2020_pct",
    "share_change_percentage_points",
    "country_code",
    "country_name",
    "geographical_zone",
    "mapping_status",
]

print("=" * 72)
print("PHASE 58 — SEMICONDUCTOR PARTNER SHIFT ANALYSIS")
print("=" * 72)

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

df = pd.read_csv(INPUT_FILE, low_memory=False)

missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

print(f"\nInput file: {INPUT_FILE.name}")
print(f"Input rows: {len(df):,}")

# ------------------------------------------------------------
# 1. Normalize and validate
# ------------------------------------------------------------

df["hs6"] = df["hs6"].astype(str).str.strip().str.zfill(6)
df["trade_direction"] = df["trade_direction"].astype(str).str.strip()
df["country_code"] = (
    df["country_code"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.strip()
    .str.zfill(3)
)

numeric_columns = [
    "value_2017_thousand_yen",
    "value_2020_thousand_yen",
    "value_change_thousand_yen",
    "value_change_trillion_yen",
    "share_2017_pct",
    "share_2020_pct",
    "share_change_percentage_points",
]

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")

if df[numeric_columns].isna().any().any():
    bad_counts = df[numeric_columns].isna().sum()
    bad_counts = bad_counts[bad_counts > 0]
    raise ValueError(f"Missing/non-numeric values detected:\n{bad_counts}")

key_columns = ["hs6", "trade_direction", "country_code"]
duplicate_mask = df.duplicated(key_columns, keep=False)

if duplicate_mask.any():
    duplicate_file = AGG / "58_duplicate_partner_keys.csv"
    df.loc[duplicate_mask].sort_values(key_columns).to_csv(
        duplicate_file, index=False, encoding="utf-8-sig"
    )
    raise ValueError(
        f"Duplicate partner keys found: {duplicate_mask.sum():,} rows. "
        f"Details saved to {duplicate_file}"
    )

# ------------------------------------------------------------
# 2. Recalculate changes from year values
# ------------------------------------------------------------

df["value_change_thousand_yen"] = (
    df["value_2020_thousand_yen"] -
    df["value_2017_thousand_yen"]
)

# 1 trillion yen = 1,000,000,000 thousand yen
df["value_change_trillion_yen"] = (
    df["value_change_thousand_yen"] / 1_000_000_000
)

# Percentage change: undefined when 2017 value is zero
df["value_change_pct_recalculated"] = np.where(
    df["value_2017_thousand_yen"] != 0,
    (
        df["value_change_thousand_yen"] /
        df["value_2017_thousand_yen"]
    ) * 100,
    np.nan,
)

df["value_change_pct_status"] = np.where(
    df["value_2017_thousand_yen"] == 0,
    "Undefined: 2017 value is zero",
    "Calculated",
)

# Recalculate partner share changes in percentage points
df["share_change_percentage_points"] = (
    df["share_2020_pct"] - df["share_2017_pct"]
)

# ------------------------------------------------------------
# 3. Add interpretable indicators and rankings
# ------------------------------------------------------------

df["value_change_direction"] = np.select(
    [
        df["value_change_thousand_yen"] > 0,
        df["value_change_thousand_yen"] < 0,
    ],
    ["Increase", "Decrease"],
    default="No change",
)

df["share_change_direction"] = np.select(
    [
        df["share_change_percentage_points"] > 0,
        df["share_change_percentage_points"] < 0,
    ],
    ["Share increased", "Share decreased"],
    default="Share unchanged",
)

group_columns = ["hs6", "trade_direction"]

df["rank_2020_value"] = (
    df.groupby(group_columns)["value_2020_thousand_yen"]
    .rank(method="min", ascending=False)
    .astype(int)
)

df["rank_2017_value"] = (
    df.groupby(group_columns)["value_2017_thousand_yen"]
    .rank(method="min", ascending=False)
    .astype(int)
)

df["rank_change"] = df["rank_2017_value"] - df["rank_2020_value"]

# ------------------------------------------------------------
# 4. Create full report and ranked subsets
# ------------------------------------------------------------

sort_columns = [
    "hs6",
    "trade_direction",
    "value_change_thousand_yen",
]

full_report = df.sort_values(
    sort_columns,
    ascending=[True, True, False],
).copy()

gainers = df[df["value_change_thousand_yen"] > 0].copy()
gainers = gainers.sort_values(
    "value_change_thousand_yen", ascending=False
)

losers = df[df["value_change_thousand_yen"] < 0].copy()
losers = losers.sort_values(
    "value_change_thousand_yen", ascending=True
)

share_increases = df[
    df["share_change_percentage_points"] > 0
].copy()
share_increases = share_increases.sort_values(
    "share_change_percentage_points", ascending=False
)

share_decreases = df[
    df["share_change_percentage_points"] < 0
].copy()
share_decreases = share_decreases.sort_values(
    "share_change_percentage_points", ascending=True
)

# ------------------------------------------------------------
# 5. Save CSV outputs
# ------------------------------------------------------------

full_report.to_csv(OUTPUT_FULL, index=False, encoding="utf-8-sig")
gainers.to_csv(OUTPUT_GAINERS, index=False, encoding="utf-8-sig")
losers.to_csv(OUTPUT_LOSERS, index=False, encoding="utf-8-sig")
share_increases.to_csv(OUTPUT_SHARE_UP, index=False, encoding="utf-8-sig")
share_decreases.to_csv(OUTPUT_SHARE_DOWN, index=False, encoding="utf-8-sig")

print("\nSaved outputs:")
for path in [
    OUTPUT_FULL,
    OUTPUT_GAINERS,
    OUTPUT_LOSERS,
    OUTPUT_SHARE_UP,
    OUTPUT_SHARE_DOWN,
]:
    print(f"  {path.name} | {path.stat().st_size:,} bytes")

# ------------------------------------------------------------
# 6. Aggregate reconciliation by HS6 and direction
# ------------------------------------------------------------

reconciliation = (
    df.groupby(group_columns, as_index=False)
    .agg(
        partner_rows=("country_code", "count"),
        export_import_value_2017_thousand_yen=(
            "value_2017_thousand_yen", "sum"
        ),
        export_import_value_2020_thousand_yen=(
            "value_2020_thousand_yen", "sum"
        ),
        net_partner_value_change_thousand_yen=(
            "value_change_thousand_yen", "sum"
        ),
    )
)

reconciliation["net_partner_value_change_trillion_yen"] = (
    reconciliation["net_partner_value_change_thousand_yen"] /
    1_000_000_000
)

# ------------------------------------------------------------
# 7. Generate text summary
# ------------------------------------------------------------

lines = []
lines.append("PHASE 58 — SEMICONDUCTOR PARTNER SHIFT ANALYSIS")
lines.append("=" * 65)
lines.append(f"Input rows: {len(df):,}")
lines.append(f"Unique partner keys: {df[key_columns].drop_duplicates().shape[0]:,}")
lines.append("Comparison: 2017 vs 2020")
lines.append("Value unit: trillion yen unless otherwise stated")
lines.append("")

lines.append("PARTNER VALUE INCREASES — TOP 15")
lines.append("-" * 65)

for _, row in gainers.head(15).iterrows():
    lines.append(
        f"HS6 {row['hs6']} | {row['trade_direction']} | "
        f"{row['country_name']} ({row['country_code']}) | "
        f"Change: {row['value_change_trillion_yen']:+.6f} T yen | "
        f"Share: {row['share_2017_pct']:.2f}% -> "
        f"{row['share_2020_pct']:.2f}% "
        f"({row['share_change_percentage_points']:+.2f} pp)"
    )

lines.append("")
lines.append("PARTNER VALUE DECREASES — TOP 15")
lines.append("-" * 65)

for _, row in losers.head(15).iterrows():
    lines.append(
        f"HS6 {row['hs6']} | {row['trade_direction']} | "
        f"{row['country_name']} ({row['country_code']}) | "
        f"Change: {row['value_change_trillion_yen']:+.6f} T yen | "
        f"Share: {row['share_2017_pct']:.2f}% -> "
        f"{row['share_2020_pct']:.2f}% "
        f"({row['share_change_percentage_points']:+.2f} pp)"
    )

lines.append("")
lines.append("LARGEST PARTNER SHARE INCREASES — TOP 15")
lines.append("-" * 65)

for _, row in share_increases.head(15).iterrows():
    lines.append(
        f"HS6 {row['hs6']} | {row['trade_direction']} | "
        f"{row['country_name']} ({row['country_code']}) | "
        f"Share change: "
        f"{row['share_change_percentage_points']:+.2f} pp | "
        f"Value change: {row['value_change_trillion_yen']:+.6f} T yen"
    )

lines.append("")
lines.append("LARGEST PARTNER SHARE DECREASES — TOP 15")
lines.append("-" * 65)

for _, row in share_decreases.head(15).iterrows():
    lines.append(
        f"HS6 {row['hs6']} | {row['trade_direction']} | "
        f"{row['country_name']} ({row['country_code']}) | "
        f"Share change: "
        f"{row['share_change_percentage_points']:+.2f} pp | "
        f"Value change: {row['value_change_trillion_yen']:+.6f} T yen"
    )

lines.append("")
lines.append("AGGREGATE RECONCILIATION BY HS6 AND DIRECTION")
lines.append("-" * 65)

for _, row in reconciliation.sort_values(group_columns).iterrows():
    lines.append(
        f"HS6 {row['hs6']} | {row['trade_direction']} | "
        f"Partners: {int(row['partner_rows'])} | "
        f"2017: {row['export_import_value_2017_thousand_yen'] / 1e9:.6f} T yen | "
        f"2020: {row['export_import_value_2020_thousand_yen'] / 1e9:.6f} T yen | "
        f"Change: {row['net_partner_value_change_trillion_yen']:+.6f} T yen"
    )

lines.append("")
lines.append("INTERPRETATION NOTES")
lines.append("-" * 65)
lines.append(
    "Value change measures the absolute change in trade value "
    "between 2017 and 2020."
)
lines.append(
    "Share change is measured in percentage points, not percent."
)
lines.append(
    "A partner's share can rise even when its trade value falls "
    "if the total HS6-direction trade value falls faster."
)
lines.append(
    "Percentage change is undefined for partners with zero 2017 value."
)
lines.append(
    "These are partner-level trade statistics, not company-level "
    "market shares or causal explanations."
)

OUTPUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

print(f"\nSummary saved: {OUTPUT_SUMMARY.name}")

print("\nReconciliation:")
print(reconciliation.to_string(index=False))

print("\nPhase 58 completed successfully.")
