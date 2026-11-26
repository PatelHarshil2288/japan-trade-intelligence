
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT = AGG / "58_semiconductor_partner_shift_full.csv"

OUTPUT_FULL = AGG / "59_semiconductor_country_aggregate_shifts.csv"
OUTPUT_GAINERS = AGG / "59_semiconductor_country_top_gainers.csv"
OUTPUT_LOSERS = AGG / "59_semiconductor_country_top_losers.csv"
OUTPUT_SUMMARY = AGG / "59_semiconductor_country_shift_summary.txt"

print("=" * 72)
print("PHASE 59 — COUNTRY-LEVEL SEMICONDUCTOR PARTNER SHIFTS")
print("=" * 72)

if not INPUT.exists():
    raise FileNotFoundError(f"Input not found: {INPUT}")

df = pd.read_csv(INPUT, low_memory=False)

required = [
    "hs6",
    "trade_direction",
    "country_code",
    "country_name",
    "value_2017_thousand_yen",
    "value_2020_thousand_yen",
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

print(f"Input rows: {len(df):,}")

for col in ["value_2017_thousand_yen", "value_2020_thousand_yen"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

if df[["value_2017_thousand_yen", "value_2020_thousand_yen"]].isna().any().any():
    raise ValueError("Missing or non-numeric trade values found.")

df["country_code"] = (
    df["country_code"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.strip()
    .str.zfill(3)
)

# Aggregate all three HS6 codes to country and direction.
group_cols = ["country_code", "country_name", "trade_direction"]

country = (
    df.groupby(group_cols, as_index=False)
    .agg(
        hs6_codes=("hs6", "nunique"),
        value_2017_thousand_yen=("value_2017_thousand_yen", "sum"),
        value_2020_thousand_yen=("value_2020_thousand_yen", "sum"),
    )
)

country["value_change_thousand_yen"] = (
    country["value_2020_thousand_yen"] -
    country["value_2017_thousand_yen"]
)

country["value_change_trillion_yen"] = (
    country["value_change_thousand_yen"] / 1_000_000_000
)

country["value_change_pct"] = np.where(
    country["value_2017_thousand_yen"] != 0,
    country["value_change_thousand_yen"] /
    country["value_2017_thousand_yen"] * 100,
    np.nan,
)

country["value_change_pct_status"] = np.where(
    country["value_2017_thousand_yen"] == 0,
    "Undefined: 2017 value is zero",
    "Calculated",
)

# Calculate each country's share of the combined three-code total
# within its trade direction.
direction_totals = (
    country.groupby("trade_direction", as_index=False)
    .agg(
        total_2017_thousand_yen=("value_2017_thousand_yen", "sum"),
        total_2020_thousand_yen=("value_2020_thousand_yen", "sum"),
    )
)

country = country.merge(direction_totals, on="trade_direction", how="left")

country["share_2017_pct"] = (
    country["value_2017_thousand_yen"] /
    country["total_2017_thousand_yen"] * 100
)

country["share_2020_pct"] = (
    country["value_2020_thousand_yen"] /
    country["total_2020_thousand_yen"] * 100
)

country["share_change_percentage_points"] = (
    country["share_2020_pct"] - country["share_2017_pct"]
)

country["value_change_direction"] = np.select(
    [
        country["value_change_thousand_yen"] > 0,
        country["value_change_thousand_yen"] < 0,
    ],
    ["Increase", "Decrease"],
    default="No change",
)

country["share_change_direction"] = np.select(
    [
        country["share_change_percentage_points"] > 0,
        country["share_change_percentage_points"] < 0,
    ],
    ["Share increased", "Share decreased"],
    default="Share unchanged",
)

country["rank_2017"] = (
    country.groupby("trade_direction")["value_2017_thousand_yen"]
    .rank(method="min", ascending=False)
    .astype(int)
)

country["rank_2020"] = (
    country.groupby("trade_direction")["value_2020_thousand_yen"]
    .rank(method="min", ascending=False)
    .astype(int)
)

country["rank_change"] = country["rank_2017"] - country["rank_2020"]

country = country.sort_values(
    ["trade_direction", "value_change_thousand_yen"],
    ascending=[True, False],
)

# Overall country-level gainers and losers, keeping export/import separate.
gainers = country[country["value_change_thousand_yen"] > 0].copy()
gainers = gainers.sort_values(
    ["trade_direction", "value_change_thousand_yen"],
    ascending=[True, False],
)

losers = country[country["value_change_thousand_yen"] < 0].copy()
losers = losers.sort_values(
    ["trade_direction", "value_change_thousand_yen"],
    ascending=[True, True],
)

country.to_csv(OUTPUT_FULL, index=False, encoding="utf-8-sig")
gainers.to_csv(OUTPUT_GAINERS, index=False, encoding="utf-8-sig")
losers.to_csv(OUTPUT_LOSERS, index=False, encoding="utf-8-sig")

# Summarize totals and verify changes.
summary_totals = (
    df.groupby("trade_direction", as_index=False)
    .agg(
        value_2017_thousand_yen=("value_2017_thousand_yen", "sum"),
        value_2020_thousand_yen=("value_2020_thousand_yen", "sum"),
    )
)

summary_totals["change_trillion_yen"] = (
    summary_totals["value_2020_thousand_yen"] -
    summary_totals["value_2017_thousand_yen"]
) / 1_000_000_000

lines = [
    "PHASE 59 — COUNTRY-LEVEL SEMICONDUCTOR PARTNER SHIFTS",
    "=" * 68,
    f"Input rows: {len(df):,}",
    f"Country-direction rows: {len(country):,}",
    "Scope: HS6 854231, 854232, 854239",
    "Period: 2017 vs 2020",
    "Values: trillion yen",
    "",
    "TOTALS BY TRADE DIRECTION",
    "-" * 68,
]

for _, row in summary_totals.iterrows():
    lines.append(
        f"{row['trade_direction']}: "
        f"2017={row['value_2017_thousand_yen']/1e9:.6f} T yen; "
        f"2020={row['value_2020_thousand_yen']/1e9:.6f} T yen; "
        f"change={row['change_trillion_yen']:+.6f} T yen"
    )

for direction in ["Export", "Import"]:
    lines.extend([
        "",
        f"TOP COUNTRY VALUE GAINERS — {direction.upper()}",
        "-" * 68,
    ])

    subset = gainers[gainers["trade_direction"] == direction].head(10)
    for _, row in subset.iterrows():
        lines.append(
            f"{row['country_name']} ({row['country_code']}): "
            f"{row['value_change_trillion_yen']:+.6f} T yen; "
            f"share change {row['share_change_percentage_points']:+.2f} pp"
        )

    lines.extend([
        "",
        f"TOP COUNTRY VALUE LOSERS — {direction.upper()}",
        "-" * 68,
    ])

    subset = losers[losers["trade_direction"] == direction].head(10)
    for _, row in subset.iterrows():
        lines.append(
            f"{row['country_name']} ({row['country_code']}): "
            f"{row['value_change_trillion_yen']:+.6f} T yen; "
            f"share change {row['share_change_percentage_points']:+.2f} pp"
        )

lines.extend([
    "",
    "Interpretation:",
    "Country totals combine the three selected HS6 codes.",
    "Exports and imports are analyzed separately.",
    "Share change is in percentage points.",
    "This is partner-level trade, not company-level market share.",
])

OUTPUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

print("\nOutputs saved:")
for path in [OUTPUT_FULL, OUTPUT_GAINERS, OUTPUT_LOSERS, OUTPUT_SUMMARY]:
    print(f"  {path.name} ({path.stat().st_size:,} bytes)")

print("\nAggregate reconciliation:")
print(summary_totals.to_string(index=False))

print("\nPhase 59 completed successfully.")
