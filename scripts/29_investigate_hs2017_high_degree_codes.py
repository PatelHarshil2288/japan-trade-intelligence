from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")

INPUT = (
    ROOT
    / "data"
    / "processed"
    / "aggregated"
    / "22_hs_concordance_relationships.csv"
)

OUTPUT_DIR = ROOT / "data" / "processed" / "aggregated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CODES = ["854231", "854232", "854239"]

print("=" * 80)
print("PHASE 5.9 — INVESTIGATE HS2017 HIGH-DEGREE MAPPINGS")
print("=" * 80)

print(f"\nReading relationship file:")
print(INPUT)

df = pd.read_csv(
    INPUT,
    dtype=str,
    low_memory=False
)

print("\nInput shape:", df.shape)
print("Columns:", list(df.columns))

required = {
    "newer_edition",
    "newer_code",
    "older_edition",
    "older_code",
    "relationship",
    "source_file",
    "source_sheet",
    "ex_marker",
}

missing = required - set(df.columns)

if missing:
    raise ValueError(
        f"Missing required columns: {sorted(missing)}"
    )

# Restrict to HS2017 -> HS2012 relationships
subset = df[
    (df["newer_edition"] == "2017")
    & (df["older_edition"] == "2012")
    & (df["newer_code"].isin(TARGET_CODES))
].copy()

print("\nTarget relationship rows:", len(subset))

if subset.empty:
    raise ValueError(
        "No matching HS2017 -> HS2012 relationships found."
    )

# Sort for easier inspection
subset = subset.sort_values(
    ["newer_code", "older_code"]
)

# Save all original relationship rows for the three target codes
detail_path = (
    OUTPUT_DIR
    / "29_hs2017_high_degree_relationship_details.csv"
)

subset.to_csv(
    detail_path,
    index=False,
    encoding="utf-8-sig"
)

# Summarize each target code
summary_rows = []

for code in TARGET_CODES:
    group = subset[subset["newer_code"] == code]

    summary_rows.append({
        "hs2017_code": code,
        "relationship_rows": len(group),
        "unique_hs2012_codes": group["older_code"].nunique(),
        "unique_relationship_types": group["relationship"].nunique(),
        "relationship_types": "; ".join(
            sorted(group["relationship"].dropna().unique())
        ),
        "ex_marker_values": "; ".join(
            sorted(group["ex_marker"].dropna().unique())
        ),
        "source_files": "; ".join(
            sorted(group["source_file"].dropna().unique())
        ),
        "source_sheets": "; ".join(
            sorted(group["source_sheet"].dropna().unique())
        ),
    })

summary = pd.DataFrame(summary_rows)

summary_path = (
    OUTPUT_DIR
    / "29_hs2017_high_degree_relationship_summary.csv"
)

summary.to_csv(
    summary_path,
    index=False,
    encoding="utf-8-sig"
)

# Check whether any target code has repeated older-code relationships
duplicate_pairs = subset[
    subset.duplicated(
        subset=["newer_code", "older_code"],
        keep=False
    )
].copy()

duplicate_path = (
    OUTPUT_DIR
    / "29_hs2017_high_degree_duplicate_pairs.csv"
)

duplicate_pairs.to_csv(
    duplicate_path,
    index=False,
    encoding="utf-8-sig"
)

print("\nTARGET CODE SUMMARY")
print(summary.to_string(index=False))

print("\nDuplicate newer/older code pairs:", len(duplicate_pairs))

print("\nOUTPUT FILES")
print(detail_path)
print(summary_path)
print(duplicate_path)

print("\n" + "=" * 80)
print("PHASE 5.9 COMPLETED")
print("=" * 80)