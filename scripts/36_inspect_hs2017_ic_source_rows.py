
from pathlib import Path
import pandas as pd
import re

# ------------------------------------------------------------
# Phase 36: Inspect original HS2017 -> HS2012 IC source rows
# ------------------------------------------------------------

ROOT = Path(r"D:\Japan_Trade_Intelligence")

REFERENCE = ROOT / "data" / "reference" / "hs_concordance"
AGG = ROOT / "data" / "processed" / "aggregated"

SOURCE_FILE = (
    REFERENCE
    / "HS2017toHS2012ConversionAndCorrelationTables.xlsx"
)

SHEET_NAME = "Correlation HS17-HS12"

CLASSIFICATION_FILE = AGG / "22_hs_classification_codes.csv"

OUTPUT_DETAIL = AGG / "36_hs2017_ic_original_source_rows.csv"
OUTPUT_SUMMARY = AGG / "36_hs2017_ic_source_summary.csv"

TARGET_CODES = ["854231", "854232", "854239"]


def normalize_code(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    digits = re.sub(r"\D", "", text)

    if len(digits) == 6:
        return digits

    return ""


def normalize_text(value):
    if pd.isna(value):
        return ""

    return " ".join(str(value).strip().lower().split())


def compact(value, limit=95):
    if pd.isna(value):
        return ""

    text = " ".join(str(value).split())

    if len(text) > limit:
        return text[:limit - 3] + "..."

    return text


def main():
    print("\nPHASE 36 - ORIGINAL HS2017 IC SOURCE ROW AUDIT")
    print("-" * 48)

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Source workbook not found:\n{SOURCE_FILE}")

    if not CLASSIFICATION_FILE.exists():
        raise FileNotFoundError(
            f"Classification file not found:\n{CLASSIFICATION_FILE}"
        )

    print(f"Workbook: {SOURCE_FILE.name}")
    print(f"Worksheet: {SHEET_NAME}")

    # Read original worksheet without assuming the header row.
    raw = pd.read_excel(
        SOURCE_FILE,
        sheet_name=SHEET_NAME,
        header=None,
        dtype=object,
    )

    # Locate the row containing the official column headings.
    header_row = None

    for row_index in range(min(20, len(raw))):
        values = [
            normalize_text(value)
            for value in raw.iloc[row_index].tolist()
        ]

        joined = " | ".join(values)

        if (
            "hs 2017" in joined
            and "hs 2012" in joined
            and "relationship" in joined
        ):
            header_row = row_index
            break

    if header_row is None:
        raise ValueError(
            "Could not locate the HS 2017 / HS 2012 / "
            "Relationship header row."
        )

    print(f"Header row found: Excel row {header_row + 1}")

    # The known source layout is:
    # HS 2017 | ex marker | HS 2012 | Relationship
    data = raw.iloc[header_row + 1:].copy()

    if data.shape[1] < 4:
        raise ValueError(
            f"Expected at least 4 columns, found {data.shape[1]}"
        )

    data = data.iloc[:, :4]
    data.columns = [
        "newer_code_raw",
        "ex_marker_raw",
        "older_code_raw",
        "relationship_raw",
    ]

    data["newer_code"] = data["newer_code_raw"].map(normalize_code)
    data["older_code"] = data["older_code_raw"].map(normalize_code)

    data["ex_marker"] = (
        data["ex_marker_raw"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    data["relationship"] = (
        data["relationship_raw"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    data["excel_row"] = data.index + 1

    # Keep original workbook rows for the three target codes.
    detail = data[
        data["newer_code"].isin(TARGET_CODES)
    ].copy()

    if detail.empty:
        raise ValueError(
            "No source rows found for the three target HS codes."
        )

    # Load classification descriptions.
    classifications = pd.read_csv(
        CLASSIFICATION_FILE,
        dtype="string",
        keep_default_na=False,
    )

    required = ["hs_edition", "hs6_code", "description"]

    missing = [
        column
        for column in required
        if column not in classifications.columns
    ]

    if missing:
        raise ValueError(
            f"Missing classification columns: {missing}"
        )

    classifications["hs6_code"] = (
        classifications["hs6_code"].map(normalize_code)
    )

    classifications["hs_edition"] = (
        classifications["hs_edition"].astype(str).str.strip()
    )

    # Build edition/code -> description lookup.
    description_lookup = {}

    for _, row in classifications.iterrows():
        key = (
            str(row["hs_edition"]).strip(),
            str(row["hs6_code"]).strip(),
        )

        description_lookup[key] = row["description"]

    detail["newer_description"] = detail["newer_code"].map(
        lambda code: description_lookup.get(("2017", code), "")
    )

    detail["older_description"] = detail["older_code"].map(
        lambda code: description_lookup.get(("2012", code), "")
    )

    detail["older_chapter"] = detail["older_code"].str[:2]

    # Keep raw source values and normalized fields for traceability.
    detail = detail[
        [
            "excel_row",
            "newer_code",
            "ex_marker",
            "older_code",
            "relationship",
            "older_chapter",
            "newer_description",
            "older_description",
            "newer_code_raw",
            "ex_marker_raw",
            "older_code_raw",
            "relationship_raw",
        ]
    ].sort_values(
        ["newer_code", "older_code"],
        kind="stable",
    )

    detail.to_csv(
        OUTPUT_DETAIL,
        index=False,
        encoding="utf-8-sig",
    )

    # Summarize links by target code.
    summary_rows = []

    for code in TARGET_CODES:
        subset = detail[detail["newer_code"] == code]

        summary_rows.append(
            {
                "newer_code": code,
                "relationship_rows": len(subset),
                "distinct_older_codes": subset["older_code"].nunique(),
                "ex_marked_rows": (
                    subset["ex_marker"].str.lower() == "ex"
                ).sum(),
                "relationship_types": ", ".join(
                    sorted(
                        value
                        for value in subset["relationship"].unique()
                        if value
                    )
                ),
                "older_chapters": ", ".join(
                    sorted(
                        value
                        for value in subset["older_chapter"].unique()
                        if value
                    )
                ),
                "missing_older_descriptions": (
                    subset["older_description"].eq("")
                ).sum(),
            }
        )

    summary = pd.DataFrame(summary_rows)

    summary.to_csv(
        OUTPUT_SUMMARY,
        index=False,
        encoding="utf-8-sig",
    )

    # Compact console report.
    print()
    print("TARGET CODE SUMMARY")

    for _, row in summary.iterrows():
        print(
            f"HS2017 {row['newer_code']} | "
            f"rows={row['relationship_rows']} | "
            f"older codes={row['distinct_older_codes']} | "
            f"ex={row['ex_marked_rows']} | "
            f"chapters={row['older_chapters']}"
        )

    print()
    print("SAMPLE ORIGINAL SOURCE ROWS")

    for code in TARGET_CODES:
        subset = detail[detail["newer_code"] == code].head(5)

        print(f"\nHS2017 {code}")

        for _, row in subset.iterrows():
            print(
                f"  Excel row {row['excel_row']} | "
                f"ex={row['ex_marker'] or '-'} | "
                f"HS2012 {row['older_code']} | "
                f"{row['relationship']} | "
                f"{compact(row['older_description'], 75)}"
            )

    print()
    print("OUTPUT FILES")
    print(OUTPUT_DETAIL)
    print(OUTPUT_SUMMARY)
    print("\nPHASE 36 COMPLETED")


if __name__ == "__main__":
    main()

