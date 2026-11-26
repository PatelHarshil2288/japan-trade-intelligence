
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
DATA = ROOT / "data" / "processed" / "aggregated"

INPUT = DATA / "22_hs_concordance_relationships.csv"

print("=" * 80)
print("PHASE 5.13 — AUDIT ALL EX-QUALIFIED HS RELATIONSHIPS")
print("=" * 80)

df = pd.read_csv(
    INPUT,
    dtype=str,
    low_memory=False
)

required = {
    "newer_edition",
    "newer_code",
    "ex_marker",
    "older_edition",
    "older_code",
    "relationship",
    "source_file",
    "source_sheet",
}

missing = required - set(df.columns)

if missing:
    raise ValueError(f"Missing columns: {sorted(missing)}")

# Normalize marker values for audit purposes.
df["ex_marker_normalized"] = (
    df["ex_marker"]
    .fillna("")
    .str.strip()
    .str.lower()
)

df["is_ex"] = df["ex_marker_normalized"].eq("ex")

# Chapter is the first two digits of the six-digit HS code.
df["newer_chapter"] = df["newer_code"].str[:2]
df["older_chapter"] = df["older_code"].str[:2]

df["chapter_comparison"] = "same_chapter"

valid_codes = (
    df["newer_code"].str.fullmatch(r"\d{6}", na=False)
    & df["older_code"].str.fullmatch(r"\d{6}", na=False)
)

df.loc[~valid_codes, "chapter_comparison"] = "invalid_code_format"

df.loc[
    valid_codes
    & df["newer_chapter"].ne(df["older_chapter"]),
    "chapter_comparison"
] = "cross_chapter"

ex_df = df[df["is_ex"]].copy()

print("\nTOTAL RELATIONSHIP ROWS:", len(df))
print("EX-QUALIFIED ROWS:", len(ex_df))
print(
    "EX ROW SHARE:",
    round(len(ex_df) / len(df) * 100, 4),
    "%"
)

# Summary by transition
transition_summary = (
    ex_df.groupby(
        ["newer_edition", "older_edition"],
        dropna=False
    )
    .agg(
        ex_relationship_rows=("newer_code", "size"),
        unique_newer_codes=("newer_code", "nunique"),
        unique_older_codes=("older_code", "nunique"),
        cross_chapter_rows=(
            "chapter_comparison",
            lambda x: (x == "cross_chapter").sum()
        ),
        same_chapter_rows=(
            "chapter_comparison",
            lambda x: (x == "same_chapter").sum()
        ),
    )
    .reset_index()
)

transition_summary["cross_chapter_percent"] = (
    transition_summary["cross_chapter_rows"]
    / transition_summary["ex_relationship_rows"]
    * 100
).round(2)

# Relationship type summary
type_summary = (
    ex_df.groupby(
        [
            "newer_edition",
            "older_edition",
            "relationship",
            "chapter_comparison",
        ],
        dropna=False
    )
    .size()
    .reset_index(name="relationship_rows")
)

# Detailed cross-chapter ex rows for manual review
cross_chapter_ex = ex_df[
    ex_df["chapter_comparison"] == "cross_chapter"
].copy()

cross_chapter_ex = cross_chapter_ex.sort_values(
    [
        "newer_edition",
        "newer_code",
        "older_code",
    ]
)

# Save outputs
transition_path = DATA / "33_ex_relationship_transition_summary.csv"
type_path = DATA / "33_ex_relationship_type_summary.csv"
detail_path = DATA / "33_ex_cross_chapter_relationships_for_review.csv"

transition_summary.to_csv(
    transition_path,
    index=False,
    encoding="utf-8-sig"
)

type_summary.to_csv(
    type_path,
    index=False,
    encoding="utf-8-sig"
)

cross_chapter_ex.to_csv(
    detail_path,
    index=False,
    encoding="utf-8-sig"
)

print("\nEX RELATIONSHIPS BY TRANSITION")
print(transition_summary.to_string(index=False))

print("\nEX RELATIONSHIPS BY TYPE AND CHAPTER COMPARISON")
print(type_summary.to_string(index=False))

print("\nCROSS-CHAPTER EX ROWS FOR REVIEW:", len(cross_chapter_ex))

print("\nOUTPUT FILES")
print(transition_path)
print(type_path)
print(detail_path)

print("\n" + "=" * 80)
print("PHASE 5.13 COMPLETED")
print("=" * 80)
