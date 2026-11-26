
from pathlib import Path
import pandas as pd

BASE = Path(r"D:\Japan_Trade_Intelligence")
DATA = BASE / "data" / "processed" / "aggregated"

REL_FILE = DATA / "23_hs_mapping_degree_diagnostics_corrected.csv"
CLASS_FILE = DATA / "22_hs_classification_codes.csv"

OUT_TOP = DATA / "25_high_degree_mapping_codes.csv"
OUT_MISMATCH = DATA / "25_relationship_label_mismatches.csv"
OUT_AUDIT = DATA / "25_mapping_anomaly_audit_summary.csv"

print("=" * 80)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 5.8 — HS MAPPING ANOMALY INVESTIGATION")
print("=" * 80)

# ---------------------------------------------------------
# 1. Load source diagnostics and classifications
# ---------------------------------------------------------

rel = pd.read_csv(REL_FILE, dtype=str)
classification = pd.read_csv(CLASS_FILE, dtype=str)

rel["older_code_count"] = pd.to_numeric(
    rel["older_code_count"], errors="coerce"
)
rel["newer_code_count"] = pd.to_numeric(
    rel["newer_code_count"], errors="coerce"
)

print("\nRelationship rows:", len(rel))
print("Classification rows:", len(classification))

# ---------------------------------------------------------
# 2. Check relationship labels against calculated degrees
# ---------------------------------------------------------

def expected_relationship(row):
    newer_degree = row["older_code_count"]
    older_degree = row["newer_code_count"]

    if newer_degree == 1 and older_degree == 1:
        return "1:1"
    elif newer_degree > 1 and older_degree == 1:
        return "1:n"
    elif newer_degree == 1 and older_degree > 1:
        return "n:1"
    else:
        return "n:n"


rel["calculated_relationship"] = rel.apply(
    expected_relationship, axis=1
)

rel["relationship_match"] = (
    rel["relationship"] == rel["calculated_relationship"]
)

mismatches = rel[~rel["relationship_match"]].copy()

print("\nRELATIONSHIP LABEL VALIDATION")
print("Matching rows:", int(rel["relationship_match"].sum()))
print("Mismatching rows:", len(mismatches))

if len(mismatches):
    print("\nMismatch breakdown:")
    print(
        mismatches.groupby(
            ["relationship", "calculated_relationship"]
        ).size().to_string()
    )

    mismatches.to_csv(
        OUT_MISMATCH,
        index=False,
        encoding="utf-8-sig"
    )

# ---------------------------------------------------------
# 3. Identify high-degree codes
# ---------------------------------------------------------

newer_codes = (
    rel.groupby(
        ["newer_edition", "older_edition", "newer_code"]
    )
    .agg(
        older_code_count=("older_code", "nunique"),
        relationship_rows=("older_code", "size")
    )
    .reset_index()
    .rename(columns={"newer_code": "code"})
    .assign(mapping_direction="newer_to_older")
)

older_codes = (
    rel.groupby(
        ["newer_edition", "older_edition", "older_code"]
    )
    .agg(
        newer_code_count=("newer_code", "nunique"),
        relationship_rows=("newer_code", "size")
    )
    .reset_index()
    .rename(columns={"older_code": "code"})
    .assign(mapping_direction="older_to_newer")
)

newer_codes = newer_codes.rename(
    columns={"older_code_count": "degree"}
)
older_codes = older_codes.rename(
    columns={"newer_code_count": "degree"}
)

high_degree = pd.concat(
    [
        newer_codes[
            ["newer_edition", "older_edition", "code",
             "degree", "relationship_rows", "mapping_direction"]
        ],
        older_codes[
            ["newer_edition", "older_edition", "code",
             "degree", "relationship_rows", "mapping_direction"]
        ]
    ],
    ignore_index=True
)

high_degree = high_degree.sort_values(
    "degree", ascending=False
)

# ---------------------------------------------------------
# 4. Attach classification descriptions where available
# ---------------------------------------------------------

classification["hs_edition"] = (
    classification["hs_edition"].astype(str)
)

classification["code"] = (
    classification["code"].astype(str).str.zfill(6)
)

high_degree = high_degree.merge(
    classification[
        ["hs_edition", "code", "description"]
    ].drop_duplicates(["hs_edition", "code"]),
    left_on=["newer_edition", "code"],
    right_on=["hs_edition", "code"],
    how="left"
)

high_degree = high_degree.merge(
    classification[
        ["hs_edition", "code", "description"]
    ].drop_duplicates(["hs_edition", "code"]),
    left_on=["older_edition", "code"],
    right_on=["hs_edition", "code"],
    how="left",
    suffixes=("_newer", "_older")
)

high_degree.to_csv(
    OUT_TOP,
    index=False,
    encoding="utf-8-sig"
)

print("\nTOP 30 HIGHEST-DEGREE MAPPINGS")
print(
    high_degree.head(30).to_string(index=False)
)

# ---------------------------------------------------------
# 5. Special-code and classification coverage audit
# ---------------------------------------------------------

classification_keys = set(
    zip(classification["hs_edition"], classification["code"])
)

coverage_rows = []

for edition_column, code_column in [
    ("newer_edition", "newer_code"),
    ("older_edition", "older_code")
]:
    unique_codes = rel[
        [edition_column, code_column]
    ].drop_duplicates()

    matched = sum(
        (str(row[edition_column]), str(row[code_column]).zfill(6))
        in classification_keys
        for _, row in unique_codes.iterrows()
    )

    coverage_rows.append({
        "edition": edition_column,
        "unique_codes": len(unique_codes),
        "matched_to_classification": matched,
        "unmatched_codes": len(unique_codes) - matched
    })

coverage = pd.DataFrame(coverage_rows)

print("\nCLASSIFICATION COVERAGE")
print(coverage.to_string(index=False))

# ---------------------------------------------------------
# 6. Transition-level anomaly summary
# ---------------------------------------------------------

summary = (
    high_degree.groupby(
        ["newer_edition", "older_edition", "mapping_direction"]
    )
    .agg(
        unique_codes=("code", "nunique"),
        maximum_degree=("degree", "max"),
        codes_degree_over_10=("degree", lambda x: (x > 10).sum()),
        codes_degree_over_25=("degree", lambda x: (x > 25).sum()),
        codes_degree_over_50=("degree", lambda x: (x > 50).sum())
    )
    .reset_index()
)

summary.to_csv(
    OUT_AUDIT,
    index=False,
    encoding="utf-8-sig"
)

print("\nANOMALY SUMMARY")
print(summary.to_string(index=False))

print("\nOUTPUT FILES")
print(OUT_TOP)
print(OUT_MISMATCH if len(mismatches) else "No mismatch file required")
print(OUT_AUDIT)

print("\n" + "=" * 80)
print("PHASE 5.8 INVESTIGATION COMPLETED")
print("=" * 80)
