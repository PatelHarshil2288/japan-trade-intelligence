
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT_FILE = AGG / "36_hs2017_ic_original_source_rows.csv"

OUTPUT_COMPARISON = AGG / "38_hs2017_ic_mapping_set_comparison.csv"
OUTPUT_DIFFERENCES = AGG / "38_hs2017_ic_mapping_set_differences.csv"

TARGET_CODES = ["854231", "854232", "854239"]


def main():
    print("\nPHASE 38 - COMPARE HS2017 IC MAPPING SETS")
    print("-" * 44)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found:\n{INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE, dtype="string", keep_default_na=False)
    df = df[df["newer_code"].isin(TARGET_CODES)].copy()

    required = [
        "newer_code",
        "older_code",
        "ex_marker",
        "relationship",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Build exact mapping signatures for each newer code.
    mapping_sets = {}

    for code in TARGET_CODES:
        subset = df[df["newer_code"] == code]

        signatures = set(
            zip(
                subset["older_code"],
                subset["ex_marker"],
                subset["relationship"],
            )
        )

        mapping_sets[code] = signatures

    base_code = TARGET_CODES[0]
    base_set = mapping_sets[base_code]

    comparison_rows = []

    for code in TARGET_CODES:
        current = mapping_sets[code]

        comparison_rows.append(
            {
                "base_code": base_code,
                "comparison_code": code,
                "base_mapping_rows": len(base_set),
                "comparison_mapping_rows": len(current),
                "common_mapping_rows": len(base_set & current),
                "base_only_rows": len(base_set - current),
                "comparison_only_rows": len(current - base_set),
                "identical_mapping_set": base_set == current,
            }
        )

    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(
        OUTPUT_COMPARISON,
        index=False,
        encoding="utf-8-sig",
    )

    # Write every mapping row that differs from the base code.
    difference_rows = []

    for code in TARGET_CODES[1:]:
        current = mapping_sets[code]

        for older_code, ex_marker, relationship in sorted(
            base_set - current
        ):
            difference_rows.append(
                {
                    "difference_type": "base_only",
                    "newer_code": base_code,
                    "older_code": older_code,
                    "ex_marker": ex_marker,
                    "relationship": relationship,
                    "comparison_code": code,
                }
            )

        for older_code, ex_marker, relationship in sorted(
            current - base_set
        ):
            difference_rows.append(
                {
                    "difference_type": "comparison_only",
                    "newer_code": code,
                    "older_code": older_code,
                    "ex_marker": ex_marker,
                    "relationship": relationship,
                    "comparison_code": code,
                }
            )

    differences = pd.DataFrame(
        difference_rows,
        columns=[
            "difference_type",
            "newer_code",
            "older_code",
            "ex_marker",
            "relationship",
            "comparison_code",
        ],
    )

    differences.to_csv(
        OUTPUT_DIFFERENCES,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Codes compared: {len(TARGET_CODES)}")
    print(f"Base code: {base_code}")
    print()

    for _, row in comparison.iterrows():
        print(
            f"{row['base_code']} vs {row['comparison_code']} | "
            f"common={row['common_mapping_rows']} | "
            f"base-only={row['base_only_rows']} | "
            f"comparison-only={row['comparison_only_rows']} | "
            f"identical={row['identical_mapping_set']}"
        )

    print(f"\nDifference rows: {len(differences):,}")
    print("\nOUTPUT FILES")
    print(OUTPUT_COMPARISON)
    print(OUTPUT_DIFFERENCES)
    print("\nPHASE 38 COMPLETED")


if __name__ == "__main__":
    main()
