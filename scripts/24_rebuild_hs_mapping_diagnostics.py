
from pathlib import Path
import pandas as pd

BASE = Path(r"D:\Japan_Trade_Intelligence")
DATA = BASE / "data" / "processed" / "aggregated"

RELATIONSHIPS_FILE = DATA / "22_hs_concordance_relationships.csv"
CONVERSIONS_FILE = DATA / "22_hs_concordance_conversions.csv"

OUTPUT_REL = DATA / "23_hs_mapping_degree_diagnostics_corrected.csv"
OUTPUT_CONV = DATA / "23_hs_conversion_degree_diagnostics.csv"
OUTPUT_SUMMARY = DATA / "23_hs_mapping_degree_summary.csv"

print("=" * 80)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 5.7 — CORRECTED HS MAPPING DIAGNOSTICS")
print("=" * 80)

# ---------------------------------------------------------
# 1. Load the original standardized mapping tables
# ---------------------------------------------------------

relationships = pd.read_csv(RELATIONSHIPS_FILE, dtype=str)
conversions = pd.read_csv(CONVERSIONS_FILE, dtype=str)

print("\nSource records:")
print("Correlation relationships:", len(relationships))
print("Conversion mappings:", len(conversions))

# ---------------------------------------------------------
# 2. Correlation diagnostics
# ---------------------------------------------------------

# Number of distinct older codes for each newer code.
forward = (
    relationships.groupby(
        ["newer_edition", "older_edition", "newer_code"]
    )["older_code"]
    .nunique()
    .reset_index(name="older_code_count")
)

# Number of distinct newer codes for each older code.
reverse = (
    relationships.groupby(
        ["newer_edition", "older_edition", "older_code"]
    )["newer_code"]
    .nunique()
    .reset_index(name="newer_code_count")
)

# Correct joins use edition pair AND the relevant code.
correlation_diagnostics = relationships.merge(
    forward,
    on=["newer_edition", "older_edition", "newer_code"],
    how="left",
    validate="many_to_one"
)

correlation_diagnostics = correlation_diagnostics.merge(
    reverse,
    on=["newer_edition", "older_edition", "older_code"],
    how="left",
    validate="many_to_one"
)

# ---------------------------------------------------------
# 3. Validate correlation diagnostics
# ---------------------------------------------------------

if len(correlation_diagnostics) != len(relationships):
    raise ValueError("Correlation diagnostic row count mismatch.")

if correlation_diagnostics[
    ["older_code_count", "newer_code_count"]
].isna().any().any():
    raise ValueError("Missing mapping-degree values detected.")

correlation_diagnostics.to_csv(
    OUTPUT_REL,
    index=False,
    encoding="utf-8-sig"
)

# ---------------------------------------------------------
# 4. Conversion diagnostics
# ---------------------------------------------------------

conv_forward = (
    conversions.groupby(
        ["newer_edition", "older_edition", "newer_code"]
    )["older_code"]
    .nunique()
    .reset_index(name="older_code_count")
)

conv_reverse = (
    conversions.groupby(
        ["newer_edition", "older_edition", "older_code"]
    )["newer_code"]
    .nunique()
    .reset_index(name="newer_code_count")
)

conversion_diagnostics = conversions.merge(
    conv_forward,
    on=["newer_edition", "older_edition", "newer_code"],
    how="left",
    validate="many_to_one"
)

conversion_diagnostics = conversion_diagnostics.merge(
    conv_reverse,
    on=["newer_edition", "older_edition", "older_code"],
    how="left",
    validate="many_to_one"
)

if len(conversion_diagnostics) != len(conversions):
    raise ValueError("Conversion diagnostic row count mismatch.")

conversion_diagnostics.to_csv(
    OUTPUT_CONV,
    index=False,
    encoding="utf-8-sig"
)

# ---------------------------------------------------------
# 5. Generate transition-level summary
# ---------------------------------------------------------

summary_rows = []

for (newer, older), group in correlation_diagnostics.groupby(
    ["newer_edition", "older_edition"]
):

    summary_rows.append({
        "newer_edition": newer,
        "older_edition": older,
        "relationship_rows": len(group),
        "unique_newer_codes": group["newer_code"].nunique(),
        "unique_older_codes": group["older_code"].nunique(),
        "newer_codes_with_multiple_older_codes":
            group.loc[
                group["older_code_count"] > 1,
                "newer_code"
            ].nunique(),
        "older_codes_with_multiple_newer_codes":
            group.loc[
                group["newer_code_count"] > 1,
                "older_code"
            ].nunique(),
        "maximum_older_codes_per_newer_code":
            group["older_code_count"].max(),
        "maximum_newer_codes_per_older_code":
            group["newer_code_count"].max(),
    })

summary = pd.DataFrame(summary_rows)

summary.to_csv(
    OUTPUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)

# ---------------------------------------------------------
# 6. Final validation and report
# ---------------------------------------------------------

print("\nCORRELATION DIAGNOSTICS")
print("Output rows:", len(correlation_diagnostics))
print("Expected rows:", len(relationships))
print("Output columns:", correlation_diagnostics.columns.tolist())

print("\nCONVERSION DIAGNOSTICS")
print("Output rows:", len(conversion_diagnostics))
print("Expected rows:", len(conversions))

print("\nTRANSITION SUMMARY")
print(summary.to_string(index=False))

print("\nOUTPUT FILES")
print(OUTPUT_REL)
print(OUTPUT_CONV)
print(OUTPUT_SUMMARY)

print("\n" + "=" * 80)
print("CORRECTED MAPPING DIAGNOSTICS CREATED SUCCESSFULLY")
print("=" * 80)
