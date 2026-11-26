
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

MAPPING_FILE = AGG / "40_shared_hs2017_ic_scope_details.csv"
CLASSIFICATION_FILE = AGG / "22_hs_classification_codes.csv"

OUTPUT_DETAILS = AGG / "41_shared_mappings_with_hs2012_descriptions.csv"
OUTPUT_MISSING = AGG / "41_hs2012_description_missing_codes.csv"
OUTPUT_SUMMARY = AGG / "41_hs2012_description_join_summary.csv"


def main():
    print("\nPHASE 41 - JOIN SHARED MAPPINGS TO HS2012 DESCRIPTIONS")
    print("-" * 58)

    for file_path in [MAPPING_FILE, CLASSIFICATION_FILE]:
        if not file_path.exists():
            raise FileNotFoundError(file_path)

    mappings = pd.read_csv(
        MAPPING_FILE,
        dtype="string",
        keep_default_na=False,
    )

    classifications = pd.read_csv(
        CLASSIFICATION_FILE,
        dtype="string",
        keep_default_na=False,
    )

    required_mapping = [
        "newer_code",
        "older_code",
        "ex_marker",
        "relationship",
        "scope_type",
    ]

    required_classification = [
        "hs_edition",
        "hs6_code",
        "description",
    ]

    for column in required_mapping:
        if column not in mappings.columns:
            raise ValueError(f"Mapping file missing column: {column}")

    for column in required_classification:
        if column not in classifications.columns:
            raise ValueError(
                f"Classification file missing column: {column}"
            )

    # Find HS2012 classification records.
    edition_text = classifications["hs_edition"].str.upper()

    hs2012 = classifications[
        edition_text.str.contains("2012", regex=False)
    ].copy()

    if hs2012.empty:
        print("\nAvailable classification editions:")
        print(
            classifications["hs_edition"]
            .drop_duplicates()
            .sort_values()
            .to_string(index=False)
        )
        raise ValueError(
            "Could not identify HS2012 rows in hs_edition."
        )

    hs2012 = hs2012[
        ["hs6_code", "description"]
    ].drop_duplicates()

    # Avoid accidental many-to-many joins from duplicate code records.
    duplicate_codes = hs2012[
        hs2012.duplicated("hs6_code", keep=False)
    ]

    if not duplicate_codes.empty:
        duplicate_codes.to_csv(
            AGG / "41_hs2012_duplicate_description_codes.csv",
            index=False,
        )
        print(
            "WARNING: Duplicate HS2012 code descriptions found; "
            "saved duplicate audit."
        )

    hs2012 = hs2012.drop_duplicates("hs6_code", keep="first")

    mappings["older_code"] = mappings["older_code"].str.strip()
    hs2012["hs6_code"] = hs2012["hs6_code"].str.strip()

    result = mappings.merge(
        hs2012,
        left_on="older_code",
        right_on="hs6_code",
        how="left",
        indicator=True,
    )

    result["description_found"] = result["_merge"].eq("both")

    details = result.drop(
        columns=["hs6_code", "_merge"]
    )

    missing = details[
        ~details["description_found"]
    ][
        ["older_code", "newer_code", "ex_marker", "relationship"]
    ].drop_duplicates()

    summary = pd.DataFrame([{
        "hs2012_classification_rows": len(hs2012),
        "shared_mapping_detail_rows": len(mappings),
        "joined_rows": len(details),
        "distinct_older_codes": mappings["older_code"].nunique(),
        "distinct_older_codes_with_description": (
            details.loc[
                details["description_found"], "older_code"
            ].nunique()
        ),
        "missing_description_rows": len(missing),
        "missing_distinct_older_codes": missing["older_code"].nunique(),
    }])

    details.to_csv(OUTPUT_DETAILS, index=False)
    missing.to_csv(OUTPUT_MISSING, index=False)
    summary.to_csv(OUTPUT_SUMMARY, index=False)

    print(f"HS2012 classification codes: {len(hs2012)}")
    print(f"Shared mapping rows: {len(mappings)}")
    print(f"Distinct older codes: {mappings['older_code'].nunique()}")
    print(f"Missing description rows: {len(missing)}")
    print(
        "Distinct older codes missing descriptions: "
        f"{missing['older_code'].nunique()}"
    )

    print("\nOUTPUT FILES")
    print(OUTPUT_DETAILS)
    print(OUTPUT_MISSING)
    print(OUTPUT_SUMMARY)

    print("\nPHASE 41 COMPLETED")


if __name__ == "__main__":
    main()
