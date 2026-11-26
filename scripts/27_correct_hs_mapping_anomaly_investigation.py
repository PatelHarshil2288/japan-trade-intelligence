
from pathlib import Path
import pandas as pd

BASE = Path(r"D:\Japan_Trade_Intelligence")
DATA = BASE / "data" / "processed" / "aggregated"

REL_FILE = DATA / "23_hs_mapping_degree_diagnostics_corrected.csv"
CLASS_FILE = DATA / "22_hs_classification_codes.csv"
MISMATCH_FILE = DATA / "25_relationship_label_mismatches.csv"

OUT_TOP = DATA / "27_high_degree_mapping_codes.csv"
OUT_SUMMARY = DATA / "27_mapping_anomaly_audit_summary.csv"
OUT_COVERAGE = DATA / "27_mapping_classification_coverage.csv"
OUT_MISMATCH_SUMMARY = DATA / "27_relationship_mismatch_summary.csv"

print("=" * 80)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 5.8 — CORRECTED HS MAPPING ANOMALY INVESTIGATION")
print("=" * 80)

# ---------------------------------------------------------
# 1. Load mapping diagnostics and classification references
# ---------------------------------------------------------

rel = pd.read_csv(REL_FILE, dtype=str)
classification = pd.read_csv(CLASS_FILE, dtype=str)

rel["older_code_count"] = pd.to_numeric(
    rel["older_code_count"], errors="coerce"
)
rel["newer_code_count"] = pd.to_numeric(
    rel["newer_code_count"], errors="coerce"
)

# Confirm the actual schema discovered in Phase 5.8.
required_class_columns = {
    "hs_edition",
    "hs6_code",
    "description",
}

missing = required_class_columns - set(classification.columns)

if missing:
    raise ValueError(
        f"Classification file missing required columns: {missing}"
    )

classification["hs6_code"] = (
    classification["hs6_code"].astype(str).str.zfill(6)
)

print("\nSource relationship rows:", len(rel))
print("Classification rows:", len(classification))

# ---------------------------------------------------------
# 2. Relationship label mismatch summary
# ---------------------------------------------------------

if MISMATCH_FILE.exists():
    mismatches = pd.read_csv(MISMATCH_FILE, dtype=str)

    mismatch_summary = (
        mismatches.groupby(
            ["newer_edition", "older_edition",
             "relationship", "calculated_relationship"]
        )
        .size()
        .reset_index(name="mismatch_rows")
    )

    mismatch_summary.to_csv(
        OUT_MISMATCH_SUMMARY,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nRELATIONSHIP LABEL MISMATCH SUMMARY")
    print(mismatch_summary.to_string(index=False))
else:
    print("\nMismatch file not found; skipping mismatch summary.")

# ---------------------------------------------------------
# 3. Build newer-code mapping degrees
# ---------------------------------------------------------

newer = (
    rel.groupby(
        ["newer_edition", "older_edition", "newer_code"]
    )
    .agg(
        degree=("older_code", "nunique"),
        relationship_rows=("older_code", "size")
    )
    .reset_index()
)

newer = newer.rename(
    columns={
        "newer_edition": "edition",
        "newer_code": "hs6_code",
    }
)

newer["mapping_direction"] = "newer_to_older"

# ---------------------------------------------------------
# 4. Build older-code mapping degrees
# ---------------------------------------------------------

older = (
    rel.groupby(
        ["newer_edition", "older_edition", "older_code"]
    )
    .agg(
        degree=("newer_code", "nunique"),
        relationship_rows=("newer_code", "size")
    )
    .reset_index()
)

older = older.rename(
    columns={
        "older_edition": "edition",
        "older_code": "hs6_code",
    }
)

older["mapping_direction"] = "older_to_newer"

# ---------------------------------------------------------
# 5. Combine code-level degree records
# ---------------------------------------------------------

newer_codes = newer[
    [
        "edition",
        "hs6_code",
        "degree",
        "relationship_rows",
        "mapping_direction",
    ]
].copy()

older_codes = older[
    [
        "edition",
        "hs6_code",
        "degree",
        "relationship_rows",
        "mapping_direction",
    ]
].copy()

high_degree = pd.concat(
    [newer_codes, older_codes],
    ignore_index=True
)

# ---------------------------------------------------------
# 6. Attach classification descriptions correctly
# ---------------------------------------------------------

class_lookup = classification[
    ["hs_edition", "hs6_code", "description"]
].drop_duplicates(
    ["hs_edition", "hs6_code"]
)

# Attach description for the code's own edition.
high_degree = high_degree.merge(
    class_lookup,
    left_on=["edition", "hs6_code"],
    right_on=["hs_edition", "hs6_code"],
    how="left",
    validate="many_to_one"
)

high_degree = high_degree.drop(
    columns=["hs_edition"]
)

high_degree = high_degree.rename(
    columns={"description": "code_description"}
)

# ---------------------------------------------------------
# 7. Add transition context
# ---------------------------------------------------------

newer_context = (
    rel[["newer_edition", "older_edition"]]
    .drop_duplicates()
)

newer_context = newer_context.rename(
    columns={
        "newer_edition": "edition",
        "older_edition": "other_edition",
    }
)

older_context = (
    rel[["newer_edition", "older_edition"]]
    .drop_duplicates()
)

older_context = older_context.rename(
    columns={
        "older_edition": "edition",
        "newer_edition": "other_edition",
    }
)

high_degree = high_degree.merge(
    newer_context.assign(
        mapping_direction="newer_to_older"
    ),
    on=["edition", "mapping_direction"],
    how="left",
    validate="many_to_one"
)

high_degree = high_degree.merge(
    older_context.assign(
        mapping_direction="older_to_newer"
    ),
    on=["edition", "mapping_direction"],
    how="left",
    validate="many_to_one"
)

high_degree = high_degree.sort_values(
    ["degree", "edition"],
    ascending=[False, True]
)

high_degree.to_csv(
    OUT_TOP,
    index=False,
    encoding="utf-8-sig"
)

print("\nTOP 30 HIGHEST-DEGREE CODE MAPPINGS")
print(
    high_degree.head(30).to_string(index=False)
)

# ---------------------------------------------------------
# 8. Classification coverage by edition
# ---------------------------------------------------------

coverage_rows = []

for edition, group in rel.groupby("newer_edition"):
    newer_unique = group[
        ["newer_edition", "newer_code"]
    ].drop_duplicates()

    older_unique = group[
        ["older_edition", "older_code"]
    ].drop_duplicates()

    newer_codes_set = set(
        zip(
            newer_unique["newer_edition"],
            newer_unique["newer_code"]
        )
    )

    older_codes_set = set(
        zip(
            older_unique["older_edition"],
            older_unique["older_code"]
        )
    )

    classification_set = set(
        zip(
            classification["hs_edition"],
            classification["hs6_code"]
        )
    )

    newer_matched = len(
        newer_codes_set & classification_set
    )

    older_matched = len(
        older_codes_set & classification_set
    )

    coverage_rows.append({
        "newer_edition": edition,
        "older_edition": group["older_edition"].iloc[0],
        "newer_unique_codes": len(newer_codes_set),
        "newer_codes_matched": newer_matched,
        "newer_codes_unmatched":
            len(newer_codes_set) - newer_matched,
        "older_unique_codes": len(older_codes_set),
        "older_codes_matched": older_matched,
        "older_codes_unmatched":
            len(older_codes_set) - older_matched,
    })

coverage = pd.DataFrame(coverage_rows)

coverage.to_csv(
    OUT_COVERAGE,
    index=False,
    encoding="utf-8-sig"
)

print("\nCLASSIFICATION COVERAGE")
print(coverage.to_string(index=False))

# ---------------------------------------------------------
# 9. Mapping anomaly summary
# ---------------------------------------------------------

summary = (
    high_degree.groupby(
        ["edition", "other_edition", "mapping_direction"]
    )
    .agg(
        unique_codes=("hs6_code", "nunique"),
        maximum_degree=("degree", "max"),
        codes_degree_over_10=("degree", lambda x: (x > 10).sum()),
        codes_degree_over_25=("degree", lambda x: (x > 25).sum()),
        codes_degree_over_50=("degree", lambda x: (x > 50).sum()),
        codes_degree_over_100=("degree", lambda x: (x > 100).sum()),
    )
    .reset_index()
)

summary.to_csv(
    OUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)

print("\nMAPPING ANOMALY SUMMARY")
print(summary.to_string(index=False))

# ---------------------------------------------------------
# 10. Final output
# ---------------------------------------------------------

print("\nOUTPUT FILES")
print(OUT_TOP)
print(OUT_SUMMARY)
print(OUT_COVERAGE)
print(OUT_MISMATCH_SUMMARY)

print("\n" + "=" * 80)
print("CORRECTED HS MAPPING ANOMALY INVESTIGATION COMPLETED")
print("=" * 80)
