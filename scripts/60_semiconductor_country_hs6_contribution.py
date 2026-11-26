
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT = AGG / "58_semiconductor_partner_shift_full.csv"

OUTPUT_DETAIL = AGG / "60_semiconductor_country_hs6_contribution.csv"
OUTPUT_TOP = AGG / "60_semiconductor_top_country_hs6_drivers.csv"
OUTPUT_SUMMARY = AGG / "60_semiconductor_country_hs6_contribution_summary.txt"

print("=" * 72)
print("PHASE 60 — COUNTRY HS6 CONTRIBUTION ANALYSIS")
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

for col in ["value_2017_thousand_yen", "value_2020_thousand_yen"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

if df[["value_2017_thousand_yen", "value_2020_thousand_yen"]].isna().any().any():
    raise ValueError("Invalid trade values found.")

df["hs6"] = df["hs6"].astype(str).str.strip().str.zfill(6)
df["country_code"] = (
    df["country_code"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.strip()
    .str.zfill(3)
)

keys = ["country_code", "country_name", "trade_direction", "hs6"]

detail = (
    df.groupby(keys, as_index=False)
    .agg(
        value_2017_thousand_yen=("value_2017_thousand_yen", "sum"),
        value_2020_thousand_yen=("value_2020_thousand_yen", "sum"),
    )
)

detail["value_change_thousand_yen"] = (
    detail["value_2020_thousand_yen"] -
    detail["value_2017_thousand_yen"]
)

detail["value_change_trillion_yen"] = (
    detail["value_change_thousand_yen"] / 1_000_000_000
)

detail["change_direction"] = detail["value_change_thousand_yen"].apply(
    lambda x: "Increase" if x > 0 else ("Decrease" if x < 0 else "No change")
)

# Rank HS6 contribution within each country and trade direction.
detail["absolute_change_trillion_yen"] = (
    detail["value_change_trillion_yen"].abs()
)

detail["hs6_change_rank_within_country"] = (
    detail.groupby(["country_code", "trade_direction"])[
        "absolute_change_trillion_yen"
    ]
    .rank(method="min", ascending=False)
    .astype(int)
)

detail = detail.sort_values(
    ["trade_direction", "country_name", "absolute_change_trillion_yen"],
    ascending=[True, True, False],
)

# Keep the strongest HS6 change for each country-direction.
top_driver = detail[detail["hs6_change_rank_within_country"] == 1].copy()

detail.to_csv(OUTPUT_DETAIL, index=False, encoding="utf-8-sig")
top_driver.to_csv(OUTPUT_TOP, index=False, encoding="utf-8-sig")

# Summary: top 15 positive and negative country-HS6 changes by direction.
lines = [
    "PHASE 60 — COUNTRY HS6 CONTRIBUTION ANALYSIS",
    "=" * 68,
    "Scope: HS6 854231, 854232, 854239",
    "Period: 2017 vs 2020",
    "Values: trillion yen",
    "",
]

for direction in ["Export", "Import"]:
    subset = detail[detail["trade_direction"] == direction]

    lines.extend([
        f"TOP HS6 CONTRIBUTIONS — {direction.upper()} VALUE INCREASES",
        "-" * 68,
    ])

    for _, row in subset.nlargest(
        15, "value_change_trillion_yen"
    ).iterrows():
        lines.append(
            f"{row['country_name']} ({row['country_code']}) | "
            f"HS6 {row['hs6']} | "
            f"{row['value_change_trillion_yen']:+.6f} T yen"
        )

    lines.extend([
        "",
        f"TOP HS6 CONTRIBUTIONS — {direction.upper()} VALUE DECREASES",
        "-" * 68,
    ])

    for _, row in subset.nsmallest(
        15, "value_change_trillion_yen"
    ).iterrows():
        lines.append(
            f"{row['country_name']} ({row['country_code']}) | "
            f"HS6 {row['hs6']} | "
            f"{row['value_change_trillion_yen']:+.6f} T yen"
        )

    lines.extend([
        "",
        f"LARGEST ABSOLUTE HS6 DRIVER BY COUNTRY — {direction.upper()}",
        "-" * 68,
    ])

    for _, row in top_driver[
        top_driver["trade_direction"] == direction
    ].sort_values(
        "absolute_change_trillion_yen", ascending=False
    ).head(20).iterrows():
        lines.append(
            f"{row['country_name']} ({row['country_code']}) | "
            f"Main HS6 driver: {row['hs6']} | "
            f"Change: {row['value_change_trillion_yen']:+.6f} T yen"
        )

    lines.append("")

lines.extend([
    "Interpretation:",
    "The largest absolute HS6 change is labeled the main driver.",
    "This does not mean it explains the full country-level change.",
    "A country may have increases in one HS6 code and decreases in another.",
    "These are descriptive trade-value decompositions, not causal findings.",
])

OUTPUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

print("\nSaved:")
for path in [OUTPUT_DETAIL, OUTPUT_TOP, OUTPUT_SUMMARY]:
    print(f"  {path.name} ({path.stat().st_size:,} bytes)")

print(f"\nDetail rows: {len(detail):,}")
print(f"Country-direction main-driver rows: {len(top_driver):,}")
print("\nPhase 60 completed successfully.")
