
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT_FILE = AGG / "36_hs2017_ic_original_source_rows.csv"

OUTPUT_SUMMARY = AGG / "39_hs2017_ic_signature_audit_summary.csv"
OUTPUT_DETAILS = AGG / "39_hs2017_ic_signature_audit_details.csv"

TARGET_CODES = ["854231", "854232", "854239"]

COLUMNS = [
    "newer_code",
    "older_code",
    "ex_marker",
    "relationship",
]


def main():
    print("\nPHASE 39 - HS2017 IC SHARED SIGNATURE AUDIT")
    print("-" * 48)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(
        INPUT_FILE,
        dtype="string",
        keep_default_na=False,
    )

    df = df[df["newer_code"].isin(TARGET_CODES)].copy()

    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # A signature consists of the older code, ex marker,
    # and relationship type.
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

    shared_all = set.intersection(
        *(signature_sets[code] for code in TARGET_CODES)
    )

    union_all = set.union(
        *(signature_sets[code] for code in TARGET_CODES)
    )

    summary_rows = []
    detail_rows = []

    for code in TARGET_CODES:
        signatures = signature_sets[code]
        unique_signatures = signatures - shared_all

        summary_rows.append({
            "newer_code": code,
            "total_signatures": len(signatures),
            "shared_by_all_three": len(shared_all),
            "unique_to_this_code": len(unique_signatures),
            "only_self_mapping_unique": (
                len(unique_signatures) == 1
                and all(
                    older == code
                    and ex == ""
                    and relationship == "1:n"
                    for older, ex, relationship
                    in unique_signatures
                )
            ),
        })

        for older, ex, relationship in sorted(signatures):
            detail_rows.append({
                "newer_code": code,
                "older_code": older,
                "ex_marker": ex,
                "relationship": relationship,
                "shared_by_all_three": (
                    (older, ex, relationship) in shared_all
                ),
                "is_self_mapping": (
                    older == code
                    and ex == ""
                    and relationship == "1:n"
                ),
            })

    summary = pd.DataFrame(summary_rows)
    details = pd.DataFrame(detail_rows)

    summary.to_csv(OUTPUT_SUMMARY, index=False)
    details.to_csv(OUTPUT_DETAILS, index=False)

    print(f"Codes audited: {len(TARGET_CODES)}")
    print(f"Shared signatures across all three: {len(shared_all)}")
    print(f"Total signatures in union: {len(union_all)}")
    print(f"Summary rows: {len(summary)}")
    print(f"Detail rows: {len(details)}")

    print("\nPER-CODE SUMMARY")
    print(summary.to_string(index=False))

    print("\nOUTPUT FILES")
    print(OUTPUT_SUMMARY)
    print(OUTPUT_DETAILS)

    print("\nPHASE 39 COMPLETED")


if __name__ == "__main__":
    main()
