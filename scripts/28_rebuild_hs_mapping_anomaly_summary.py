
from pathlib import Path
import pandas as pd

BASE = Path(r"D:\Japan_Trade_Intelligence")
DATA = BASE / "data" / "processed" / "aggregated"

REL_FILE = DATA / "23_hs_mapping_degree_diagnostics_corrected.csv"
CLASS_FILE = DATA / "22_hs_classification_codes.csv"

OUT_DEGREES = DATA / "28_hs_mapping_code_degrees.csv"
OUT_SUMMARY = DATA / "28_hs_mapping_anomaly_summary.csv"

print("=" * 80)
print("PHASE 5.8 — FINAL HS MAPPING DEGREE SUMMARY")
print("=" * 80)

rel = pd.read_csv(REL_FILE, dtype=str)
classification = pd.read_csv(CLASS_FILE, dtype=str)

rel["older_code_count"] = pd.to_numeric(
    rel["older_code_count"], errors="raise"
)
rel["newer_code_count"] = pd.to_numeric(
    rel["newer_code_count"], errors="raise"
)

classification["hs6_code"] = (
    classification["hs6_code"].astype(str).str.zfill(6)
)

# Newer code -> older codes
newer = (
    rel.groupby(
        ["newer_edition", "older_edition", "newer_code"]
    )
    .agg(
        degree=("older_code", "nunique"),
        relationship_rows=("older_code", "size"),
    )
    .reset_index()
    .rename(
        columns={
            "newer_edition": "edition",
            "older_edition": "other_edition",
            "newer_code": "hs6_code",
        }
    )
)

newer["mapping_direction"] = "newer_to_older"

# Older code -> newer codes
older = (
    rel.groupby(
        ["newer_edition", "older_edition", "older_code"]
    )
    .agg(
        degree=("newer_code", "nunique"),
        relationship_rows=("newer_code", "size"),
    )
    .reset_index()
    .rename(
        columns={
            "older_edition": "edition",
            "newer_edition": "other_edition",
            "older_code": "hs6_code",
        }
    )
)

older["mapping_direction"] = "older_to_newer"

degrees = pd.concat(
    [newer, older],
    ignore_index=True
)

# Attach description using the code's own HS edition.
lookup = classification[
    ["hs_edition", "hs6_code", "description"]
].drop_duplicates(
    ["hs_edition", "hs6_code"]
)

degrees = degrees.merge(
    lookup,
    left_on=["edition", "hs6_code"],
    right_on=["hs_edition", "hs6_code"],
    how="left",
    validate="many_to_one"
)

degrees = degrees.drop(columns=["hs_edition"])
degrees = degrees.rename(
    columns={"description": "code_description"}
)

if degrees["code_description"].isna().any():
    print("WARNING: Some codes have no classification description.")

degrees.to_csv(
    OUT_DEGREES,
    index=False,
    encoding="utf-8-sig"
)

summary = (
    degrees.groupby(
        ["edition", "other_edition", "mapping_direction"]
    )
    .agg(
        unique_codes=("hs6_code", "nunique"),
        maximum_degree=("degree", "max"),
        codes_degree_over_10=("degree", lambda s: (s > 10).sum()),
        codes_degree_over_25=("degree", lambda s: (s > 25).sum()),
        codes_degree_over_50=("degree", lambda s: (s > 50).sum()),
        codes_degree_over_100=("degree", lambda s: (s > 100).sum()),
    )
    .reset_index()
)

summary.to_csv(
    OUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)

print("\nCODE DEGREE RECORDS:", len(degrees))
print("\nFINAL TRANSITION SUMMARY")
print(summary.to_string(index=False))

print("\nTOP 20 HIGH-DEGREE CODES")
print(
    degrees.sort_values("degree", ascending=False)
    .head(20)
    .to_string(index=False)
)

print("\nOUTPUT FILES")
print(OUT_DEGREES)
print(OUT_SUMMARY)

print("\n" + "=" * 80)
print("SUMMARY REBUILT SUCCESSFULLY")
print("=" * 80)
