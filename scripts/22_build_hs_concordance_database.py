
from pathlib import Path
import re
import pandas as pd

# ============================================================
# JAPAN TRADE INTELLIGENCE
# PHASE 5.5 — BUILD STANDARDIZED HS REFERENCE DATABASE
# ============================================================

BASE = Path(
    r"D:\Japan_Trade_Intelligence\data\reference\hs_concordance"
)

OUTPUT_DIR = (
    Path(r"D:\Japan_Trade_Intelligence")
    / "data" / "processed" / "aggregated"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRANSITIONS = [
    {
        "file": "HS1996 to HS1992 - Correlation and conversion tables.xls",
        "newer": "1996",
        "older": "1992",
        "correlation_sheet": "Correlation Table",
        "conversion_sheet": "Conversion Table",
    },
    {
        "file": "HS2002 to HS1996 - Correlation and conversion tables.xls",
        "newer": "2002",
        "older": "1996",
        "correlation_sheet": "Correlation table",
        "conversion_sheet": "Conversion Table",
    },
    {
        "file": "HS 2007 to HS 2002 Correlation and conversion tables.xls",
        "newer": "2007",
        "older": "2002",
        "correlation_sheet": "Correlation Tables",
        "conversion_sheet": "Conversion Tables",
    },
    {
        "file": "HS 2012 to HS 2007 Correlation and conversion tables.xls",
        "newer": "2012",
        "older": "2007",
        "correlation_sheet": "Correlation HS2012-HS2007",
        "conversion_sheet": "Conversion HS12-HS07",
    },
    {
        "file": "HS2017toHS2012ConversionAndCorrelationTables.xlsx",
        "newer": "2017",
        "older": "2012",
        "correlation_sheet": "Correlation HS17-HS12",
        "conversion_sheet": "Conversion HS17-HS12",
    },
]

UN_CLASSIFICATIONS = {
    "H0": "1992",
    "H1": "1996",
    "H2": "2002",
    "H3": "2007",
    "H4": "2012",
    "H5": "2017",
    "H6": "2022",
}

CODE_PATTERN = re.compile(r"^\d{6}$")
RELATION_PATTERN = re.compile(r"^\s*'?([1n])\s*:\s*([1n])\s*$", re.I)


def clean_code(value):
    """Return a six-digit code as text, or None."""
    if pd.isna(value):
        return None

    value = str(value).strip()

    # Excel may represent a code as a number ending in .0.
    if re.fullmatch(r"\d+\.0", value):
        value = value[:-2]

    if CODE_PATTERN.fullmatch(value):
        return value

    return None


def clean_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip()
    return value if value else None


def clean_relationship(value):
    value = clean_text(value)
    if value is None:
        return None

    match = RELATION_PATTERN.fullmatch(value)
    if match:
        return f"{match.group(1).lower()}:{match.group(2).lower()}"

    return value


def inspect_mapping_workbook(config):
    file = BASE / config["file"]

    if not file.exists():
        raise FileNotFoundError(file)

    print("\nProcessing:", file.name)

    correlation_raw = pd.read_excel(
        file,
        sheet_name=config["correlation_sheet"],
        header=None,
        dtype=object
    )

    conversion_raw = pd.read_excel(
        file,
        sheet_name=config["conversion_sheet"],
        header=None,
        dtype=object
    )

    correlation_rows = []
    for _, row in correlation_raw.iterrows():

        # Correlation layout:
        # Column 0 = newer edition code
        # Column 1 = optional "ex" marker
        # Column 2 = older edition code
        # Column 3 = relationship label

        newer_code = clean_code(row.iloc[0])
        older_code = clean_code(row.iloc[2]) if len(row) > 2 else None

        if newer_code is None or older_code is None:
            continue

        relationship = (
            clean_relationship(row.iloc[3])
            if len(row) > 3 else None
        )

        correlation_rows.append({
            "newer_edition": config["newer"],
            "newer_code": newer_code,
            "ex_marker": clean_text(row.iloc[1]),
            "older_edition": config["older"],
            "older_code": older_code,
            "relationship": relationship,
            "source_file": config["file"],
            "source_sheet": config["correlation_sheet"],
        })

    conversion_rows = []
    for _, row in conversion_raw.iterrows():

        # Conversion layout:
        # Column 0 = From (newer edition)
        # Column 1 = To (older edition)

        newer_code = clean_code(row.iloc[0])
        older_code = clean_code(row.iloc[1]) if len(row) > 1 else None

        if newer_code is None or older_code is None:
            continue

        conversion_rows.append({
            "newer_edition": config["newer"],
            "newer_code": newer_code,
            "older_edition": config["older"],
            "older_code": older_code,
            "source_file": config["file"],
            "source_sheet": config["conversion_sheet"],
        })

    print(
        "Correlation rows retained:",
        f"{len(correlation_rows):,}"
    )
    print(
        "Conversion rows retained:",
        f"{len(conversion_rows):,}"
    )

    return correlation_rows, conversion_rows


# ------------------------------------------------------------
# 1. Parse all transition workbooks
# ------------------------------------------------------------

print("=" * 80)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 5.5 — STANDARDIZED HS CONCORDANCE DATABASE")
print("=" * 80)

all_correlations = []
all_conversions = []

for config in TRANSITIONS:
    correlations, conversions = inspect_mapping_workbook(config)
    all_correlations.extend(correlations)
    all_conversions.extend(conversions)

correlation_df = pd.DataFrame(all_correlations)
conversion_df = pd.DataFrame(all_conversions)

# ------------------------------------------------------------
# 2. Parse UN Comtrade classification code lists
# ------------------------------------------------------------

print("\nProcessing UN Comtrade classification files...")

classification_rows = []

for edition_code, edition_year in UN_CLASSIFICATIONS.items():

    file = BASE / f"UNComtrade-cmd-{edition_code}.csv"

    if not file.exists():
        raise FileNotFoundError(file)

    df = pd.read_csv(
        file,
        dtype=str,
        encoding="utf-8-sig"
    )

    df["id"] = df["id"].fillna("").str.strip()
    df["isLeaf"] = df["isLeaf"].fillna("").str.strip()

    # Retain six-digit product codes only.
    # Preserve the supplied leaf flag and descriptions.
    six_digit = df[
        df["id"].str.fullmatch(r"\d{6}", na=False)
    ].copy()

    for _, row in six_digit.iterrows():
        classification_rows.append({
            "hs_edition": edition_year,
            "un_classification_id": edition_code,
            "hs6_code": row["id"],
            "description": clean_text(row["text"]),
            "parent_code": clean_text(row["parent"]),
            "is_leaf": row["isLeaf"],
            "aggregation_level": clean_text(row["aggrlevel"]),
            "standard_unit": clean_text(
                row["standardUnitAbbr"]
            ),
            "source_file": file.name,
        })

    print(
        edition_code,
        edition_year,
        "six-digit codes:",
        f"{len(six_digit):,}"
    )

classification_df = pd.DataFrame(classification_rows)

# ------------------------------------------------------------
# 3. Duplicate and mapping diagnostics
# ------------------------------------------------------------

print("\nRunning reference diagnostics...")

correlation_duplicate_count = int(
    correlation_df.duplicated(
        subset=[
            "newer_edition",
            "newer_code",
            "older_edition",
            "older_code",
            "relationship",
            "ex_marker",
        ]
    ).sum()
)

conversion_duplicate_count = int(
    conversion_df.duplicated(
        subset=[
            "newer_edition",
            "newer_code",
            "older_edition",
            "older_code",
        ]
    ).sum()
)

classification_duplicate_count = int(
    classification_df.duplicated(
        subset=["hs_edition", "hs6_code"]
    ).sum()
)

# Number of distinct older codes associated with each newer code.
correlation_degree = (
    correlation_df.groupby(
        ["newer_edition", "newer_code", "older_edition"]
    )["older_code"]
    .nunique()
    .reset_index(name="older_code_count")
)

# Number of distinct newer codes associated with each older code.
reverse_degree = (
    correlation_df.groupby(
        ["newer_edition", "older_edition", "older_code"]
    )["newer_code"]
    .nunique()
    .reset_index(name="newer_code_count")
)

relationship_summary = (
    correlation_df.groupby(
        ["newer_edition", "older_edition", "relationship"],
        dropna=False
    )
    .size()
    .reset_index(name="row_count")
)

transition_summary = []

for config in TRANSITIONS:

    corr = correlation_df[
        (correlation_df["newer_edition"] == config["newer"])
        & (correlation_df["older_edition"] == config["older"])
    ]

    conv = conversion_df[
        (conversion_df["newer_edition"] == config["newer"])
        & (conversion_df["older_edition"] == config["older"])
    ]

    transition_summary.append({
        "newer_edition": config["newer"],
        "older_edition": config["older"],
        "correlation_rows": len(corr),
        "correlation_unique_pairs": len(
            corr[["newer_code", "older_code"]].drop_duplicates()
        ),
        "conversion_rows": len(conv),
        "conversion_unique_pairs": len(
            conv[["newer_code", "older_code"]].drop_duplicates()
        ),
        "correlation_duplicate_rows": int(
            corr.duplicated(
                subset=["newer_code", "older_code", "relationship"]
            ).sum()
        ),
        "conversion_duplicate_rows": int(
            conv.duplicated(
                subset=["newer_code", "older_code"]
            ).sum()
        ),
    })

transition_summary_df = pd.DataFrame(transition_summary)

# ------------------------------------------------------------
# 4. Save standardized outputs
# ------------------------------------------------------------

correlation_path = (
    OUTPUT_DIR / "22_hs_concordance_relationships.csv"
)
conversion_path = (
    OUTPUT_DIR / "22_hs_concordance_conversions.csv"
)
classification_path = (
    OUTPUT_DIR / "22_hs_classification_codes.csv"
)
summary_path = (
    OUTPUT_DIR / "22_hs_reference_audit_summary.csv"
)
relationship_path = (
    OUTPUT_DIR / "22_hs_relationship_type_summary.csv"
)
degree_path = (
    OUTPUT_DIR / "22_hs_mapping_degree_diagnostics.csv"
)

correlation_df.to_csv(correlation_path, index=False)
conversion_df.to_csv(conversion_path, index=False)
classification_df.to_csv(classification_path, index=False)
transition_summary_df.to_csv(summary_path, index=False)
relationship_summary.to_csv(relationship_path, index=False)

degree_diagnostics = correlation_degree.merge(
    reverse_degree,
    on=["newer_edition", "older_edition"],
    how="left"
)

degree_diagnostics.to_csv(degree_path, index=False)

# ------------------------------------------------------------
# 5. Console validation
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("VALIDATION SUMMARY")
print("-" * 80)

print("Total correlation rows:", f"{len(correlation_df):,}")
print("Total conversion rows:", f"{len(conversion_df):,}")
print("Total classification rows:", f"{len(classification_df):,}")

print("\nDuplicate diagnostics:")
print("Correlation duplicate rows:", correlation_duplicate_count)
print("Conversion duplicate rows:", conversion_duplicate_count)
print("Classification duplicate rows:", classification_duplicate_count)

print("\nTRANSITION SUMMARY")
print("-" * 80)
print(transition_summary_df.to_string(index=False))

print("\nRELATIONSHIP TYPE SUMMARY")
print("-" * 80)
print(relationship_summary.to_string(index=False))

print("\nCLASSIFICATION CODE COUNTS")
print("-" * 80)
print(
    classification_df.groupby(
        ["hs_edition", "un_classification_id"]
    )["hs6_code"]
    .nunique()
    .reset_index(name="unique_hs6_codes")
    .to_string(index=False)
)

print("\nOUTPUT FILES")
print("-" * 80)

for path in [
    correlation_path,
    conversion_path,
    classification_path,
    summary_path,
    relationship_path,
    degree_path,
]:
    print(path)

print("\n" + "=" * 80)
print("STANDARDIZED HS REFERENCE DATABASE CREATED")
print("=" * 80)
