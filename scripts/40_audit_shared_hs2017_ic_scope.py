
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT_FILE = AGG / "36_hs2017_ic_original_source_rows.csv"

OUTPUT_DETAILS = AGG / "40_shared_hs2017_ic_scope_details.csv"
OUTPUT_SUMMARY = AGG / "40_shared_hs2017_ic_scope_summary.csv"

TARGET_CODES = ["854231", "854232", "854239"]

SIGNATURE_COLUMNS = [
    "older_code",
    "ex_marker",
    "relationship",
]


def main():
    print("\nPHASE 40 - AUDIT SHARED HS2017 IC MAPPING SCOPE")
    print("-" * 52)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(
        INPUT_FILE,
        dtype="string",
        keep_default_na=False,
    )

    required = ["newer_code"] + SIGNATURE_COLUMNS
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[df["newer_code"].isin(TARGET_CODES)].copy()

    # Mapping signature: older code + ex marker + relationship.
    df["signature"] = list(
        zip(
            df["older_code"],
            df["ex_marker"],
            df["relationship"],
        )
    )

    signature_sets = {
        code: set(df.loc[df["newer_code"] == code, "signature"])
        for code in TARGET_CODES
    }

    shared_signatures = set.intersection(
        *(signature_sets[code] for code in TARGET_CODES)
    )

    shared = df[df["signature"].isin(shared_signatures)].copy()

    shared["scope_type"] = shared["ex_marker"].map(
        lambda value: (
            "ex_partial_scope"
            if value.lower() == "ex"
            else "blank_marker"
        )
    )

    # Keep signature internally for accurate counting.
    details_internal = shared[
        ["newer_code"] + SIGNATURE_COLUMNS + ["scope_type", "signature"]
    ].drop_duplicates()

    # Export readable details without the internal tuple column.
    details_output = details_internal.drop(columns=["signature"])

    summary = (
        details_internal.groupby(
            ["scope_type", "ex_marker", "relationship"],
            dropna=False,
        )
        .agg(
            distinct_signatures=("signature", "nunique"),
            source_rows=("newer_code", "size"),
            codes_present=("newer_code", "nunique"),
        )
        .reset_index()
    )

    details_output.to_csv(OUTPUT_DETAILS, index=False)
    summary.to_csv(OUTPUT_SUMMARY, index=False)

    print(f"Codes audited: {len(TARGET_CODES)}")
    print(f"Shared signatures: {len(shared_signatures)}")
    print(f"Shared detail rows: {len(details_output)}")

    print("\nSCOPE SUMMARY")
    print(summary.to_string(index=False))

    print("\nOUTPUT FILES")
    print(OUTPUT_DETAILS)
    print(OUTPUT_SUMMARY)

    print("\nPHASE 40 COMPLETED")


if __name__ == "__main__":
    main()
