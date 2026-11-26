from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT = AGG / "61_semiconductor_hs6_contribution_matrix.csv"

OUTPUT_FULL = AGG / "62_semiconductor_country_hs6_driver_ranking.csv"
OUTPUT_TOP_NET = AGG / "62_semiconductor_top_net_changes.csv"
OUTPUT_TOP_DRIVERS = AGG / "62_semiconductor_top_hs6_drivers.csv"
OUTPUT_SUMMARY = AGG / "62_semiconductor_country_hs6_driver_ranking_summary.txt"

HS6_CODES = ["854231", "854232", "854239"]

CHANGE_COLUMNS = {
    "854231": "change_854231_trillion_yen",
    "854232": "change_854232_trillion_yen",
    "854239": "change_854239_trillion_yen",
}

KEYS = ["country_code", "country_name", "trade_direction"]

print("=" * 72)
print("PHASE 62 - COUNTRY x HS6 DRIVER RANKING")
print("=" * 72)

if not INPUT.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT}")

df = pd.read_csv(INPUT, low_memory=False)

required = [
    "country_code",
    "country_name",
    "trade_direction",
    "total_change_trillion_yen",
    "original_change_thousand_yen",
    "reconciliation_difference_thousand_yen",
    "largest_absolute_hs6_driver",
    *CHANGE_COLUMNS.values(),
]

missing = [col for col in required if col not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

# Normalize identifiers.
df["country_code"] = (
    df["country_code"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.strip()
    .str.zfill(3)
)

df["trade_direction"] = (
    df["trade_direction"]
    .astype(str)
    .str.strip()
)

df["country_name"] = df["country_name"].astype(str).str.strip()

# Validate trade directions.
valid_directions = {"Export", "Import"}
unexpected_directions = set(df["trade_direction"]) - valid_directions

if unexpected_directions:
    raise ValueError(
        f"Unexpected trade directions: {sorted(unexpected_directions)}"
    )

# Convert required numeric fields.
numeric_columns = [
    "total_change_trillion_yen",
    "original_change_thousand_yen",
    "reconciliation_difference_thousand_yen",
    *CHANGE_COLUMNS.values(),
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

if df[numeric_columns].isna().any().any():
    raise ValueError("Missing or non-numeric values found in numeric columns.")

# Ensure one row per country and trade direction.
if df.duplicated(KEYS).any():
    duplicates = df.loc[df.duplicated(KEYS, keep=False), KEYS]
    raise ValueError(
        "Duplicate country-direction rows found:\n"
        + duplicates.head(20).to_string(index=False)
    )

# Calculate the sum of the three HS6 contributions.
df["hs6_sum_trillion_yen"] = df[
    list(CHANGE_COLUMNS.values())
].sum(axis=1)

# Verify the HS6 contributions equal the reported net change.
df["net_reconciliation_trillion_yen"] = (
    df["hs6_sum_trillion_yen"]
    - df["total_change_trillion_yen"]
)

max_net_difference = df[
    "net_reconciliation_trillion_yen"
].abs().max()

if max_net_difference > 0.000001:
    raise ValueError(
        "HS6 contribution reconciliation failed. "
        f"Maximum difference: {max_net_difference}"
    )

# Identify the largest absolute HS6 contribution.
df["driver_hs6"] = (
    df[list(CHANGE_COLUMNS.values())]
    .abs()
    .idxmax(axis=1)
    .map({v: k for k, v in CHANGE_COLUMNS.items()})
)

df["driver_change_trillion_yen"] = df.apply(
    lambda row: row[CHANGE_COLUMNS[row["driver_hs6"]]],
    axis=1,
)

df["driver_absolute_change_trillion_yen"] = (
    df["driver_change_trillion_yen"].abs()
)

# Compare the dominant driver with the other two HS6 codes.
df["other_hs6_change_trillion_yen"] = (
    df["total_change_trillion_yen"]
    - df["driver_change_trillion_yen"]
)

df["other_hs6_absolute_change_trillion_yen"] = (
    df["other_hs6_change_trillion_yen"].abs()
)

# Determine whether the other codes reinforce or offset the driver.
def classify_relationship(row):
    driver = row["driver_change_trillion_yen"]
    other = row["other_hs6_change_trillion_yen"]

    if abs(driver) < 1e-15:
        return "No material driver"

    if abs(other) < 1e-15:
        return "No material offset or reinforcement"

    if driver * other < 0:
        return "Offset"

    return "Reinforcement"


df["driver_relationship"] = df.apply(
    classify_relationship,
    axis=1,
)

# Percentage of the dominant driver's magnitude represented by the
# combined contribution of the other two codes.
df["other_hs6_vs_driver_pct"] = (
    df["other_hs6_absolute_change_trillion_yen"]
    / df["driver_absolute_change_trillion_yen"].replace(0, pd.NA)
    * 100
)

# Net change direction.
df["net_change_direction"] = df[
    "total_change_trillion_yen"
].apply(
    lambda x: (
        "Increase" if x > 0
        else "Decrease" if x < 0
        else "No change"
    )
)

# Rank net increases and decreases within each trade direction.
df["net_increase_rank"] = (
    df.groupby("trade_direction")["total_change_trillion_yen"]
    .rank(method="min", ascending=False)
    .astype(int)
)

df["net_decrease_rank"] = (
    df.groupby("trade_direction")["total_change_trillion_yen"]
    .rank(method="min", ascending=True)
    .astype(int)
)

# Rank the largest absolute HS6 drivers within each trade direction.
df["driver_magnitude_rank"] = (
    df.groupby("trade_direction")[
        "driver_absolute_change_trillion_yen"
    ]
    .rank(method="min", ascending=False)
    .astype(int)
)

# Sort full output by trade direction and largest net increases.
df = df.sort_values(
    ["trade_direction", "net_increase_rank", "country_code"]
).reset_index(drop=True)

# Save full ranked country-direction table.
df.to_csv(OUTPUT_FULL, index=False, encoding="utf-8-sig")

# Top net increases and decreases for each trade direction.
top_net_parts = []

for direction in ["Export", "Import"]:
    subset = df[df["trade_direction"] == direction]

    increases = subset.nlargest(
        15, "total_change_trillion_yen"
    ).copy()
    increases["net_change_rank_type"] = "Top increase"

    decreases = subset.nsmallest(
        15, "total_change_trillion_yen"
    ).copy()
    decreases["net_change_rank_type"] = "Top decrease"

    top_net_parts.extend([increases, decreases])

top_net = pd.concat(top_net_parts, ignore_index=True)

top_net.to_csv(
    OUTPUT_TOP_NET,
    index=False,
    encoding="utf-8-sig",
)

# Top individual HS6 drivers by absolute change.
top_drivers_parts = []

for direction in ["Export", "Import"]:
    subset = df[df["trade_direction"] == direction]

    top = subset.nlargest(
        20, "driver_absolute_change_trillion_yen"
    ).copy()

    top_drivers_parts.append(top)

top_drivers = pd.concat(
    top_drivers_parts,
    ignore_index=True,
)

top_drivers.to_csv(
    OUTPUT_TOP_DRIVERS,
    index=False,
    encoding="utf-8-sig",
)

# Overall reconciliation by trade direction.
direction_summary = (
    df.groupby("trade_direction", as_index=False)
    .agg(
        country_direction_rows=("country_code", "size"),
        total_change_trillion_yen=(
            "total_change_trillion_yen", "sum"
        ),
        hs6_sum_trillion_yen=(
            "hs6_sum_trillion_yen", "sum"
        ),
        max_reconciliation_difference=(
            "net_reconciliation_trillion_yen",
            lambda x: x.abs().max(),
        ),
    )
)

# Write readable text summary using ASCII punctuation for compatibility.
lines = []

lines.append("PHASE 62 - COUNTRY x HS6 DRIVER RANKING")
lines.append("=" * 72)
lines.append("Period: 2017 vs 2020")
lines.append("Scope: HS6 854231, 854232, 854239")
lines.append("Values: trillion yen")
lines.append(f"Country-direction rows: {len(df)}")
lines.append(
    f"Maximum HS6 reconciliation difference: "
    f"{max_net_difference:.12f} trillion yen"
)

lines.append("")
lines.append("TOTAL NET CHANGE BY TRADE DIRECTION")
lines.append("-" * 72)

for _, row in direction_summary.iterrows():
    lines.append(
        f"{row['trade_direction']} | "
        f"Net change: {row['total_change_trillion_yen']:+.6f} T yen | "
        f"Rows: {int(row['country_direction_rows'])} | "
        f"Max difference: {row['max_reconciliation_difference']:.12f}"
    )

for direction in ["Export", "Import"]:
    subset = df[df["trade_direction"] == direction]

    lines.append("")
    lines.append(f"TOP NET INCREASES - {direction.upper()}")
    lines.append("-" * 72)

    for _, row in subset.nlargest(
        10, "total_change_trillion_yen"
    ).iterrows():
        lines.append(
            f"{row['country_name']} ({row['country_code']}) | "
            f"Net: {row['total_change_trillion_yen']:+.6f} T | "
            f"Driver HS6: {row['driver_hs6']} | "
            f"Driver: {row['driver_change_trillion_yen']:+.6f} T | "
            f"Other codes: {row['other_hs6_change_trillion_yen']:+.6f} T | "
            f"{row['driver_relationship']} | "
            f"Other/driver: {row['other_hs6_vs_driver_pct']:.1f}%"
        )

    lines.append("")
    lines.append(f"TOP NET DECREASES - {direction.upper()}")
    lines.append("-" * 72)

    for _, row in subset.nsmallest(
        10, "total_change_trillion_yen"
    ).iterrows():
        lines.append(
            f"{row['country_name']} ({row['country_code']}) | "
            f"Net: {row['total_change_trillion_yen']:+.6f} T | "
            f"Driver HS6: {row['driver_hs6']} | "
            f"Driver: {row['driver_change_trillion_yen']:+.6f} T | "
            f"Other codes: {row['other_hs6_change_trillion_yen']:+.6f} T | "
            f"{row['driver_relationship']} | "
            f"Other/driver: {row['other_hs6_vs_driver_pct']:.1f}%"
        )

    lines.append("")
    lines.append(f"LARGEST HS6 DRIVERS - {direction.upper()}")
    lines.append("-" * 72)

    for _, row in subset.nlargest(
        10, "driver_absolute_change_trillion_yen"
    ).iterrows():
        lines.append(
            f"{row['country_name']} ({row['country_code']}) | "
            f"HS6 {row['driver_hs6']} | "
            f"Driver change: {row['driver_change_trillion_yen']:+.6f} T | "
            f"Country net: {row['total_change_trillion_yen']:+.6f} T | "
            f"{row['driver_relationship']}"
        )

OUTPUT_SUMMARY.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print()
print(f"Country-direction rows: {len(df)}")
print(f"Full ranking saved: {OUTPUT_FULL.name}")
print(f"Top net changes saved: {OUTPUT_TOP_NET.name}")
print(f"Top HS6 drivers saved: {OUTPUT_TOP_DRIVERS.name}")
print(f"Summary saved: {OUTPUT_SUMMARY.name}")
print(
    "Maximum reconciliation difference: "
    f"{max_net_difference:.12f} trillion yen"
)

print()
print("Phase 62 completed successfully.")
