
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT_FILE = AGG / "36_hs2017_ic_original_source_rows.csv"

OUTPUT_CHAPTER = AGG / "37_hs2017_ic_chapter_distribution.csv"
OUTPUT_MARKER = AGG / "37_hs2017_ic_ex_marker_summary.csv"
OUTPUT_EXCEPTIONS = AGG / "37_hs2017_ic_non_ex_rows.csv"

TARGET_CODES = ["854231", "854232", "854239"]


def main():
    print("\nPHASE 37 - HS2017 IC RELATIONSHIP SCOPE SUMMARY")
    print("-" * 50)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found:\n{INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE, dtype="string", keep_default_na=False)

    required = [
        "newer_code",
        "older_code",
        "older_chapter",
        "ex_marker",
        "relationship",
    ]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    df = df[df["newer_code"].isin(TARGET_CODES)].copy()

    df["ex_marker_clean"] = df["ex_marker"].str.strip()
    df["is_ex"] = df["ex_marker_clean"].str.lower().eq("ex")
    df["is_same_chapter"] = (
        df["newer_code"].str[:2] == df["older_chapter"].str.strip()
    )

    # Chapter distribution for each newer HS code.
    chapter_summary = (
        df.groupby(
            ["newer_code", "older_chapter"],
            dropna=False,
        )
        .agg(
            relationship_rows=("older_code", "size"),
            ex_rows=("is_ex", "sum"),
            distinct_older_codes=("older_code", "nunique"),
        )
        .reset_index()
        .sort_values(["newer_code", "older_chapter"])
    )

    chapter_summary.to_csv(
        OUTPUT_CHAPTER,
        index=False,
        encoding="utf-8-sig",
    )

    # Marker and relationship-type summary.
    marker_summary = (
        df.groupby(
            ["newer_code", "ex_marker_clean", "relationship"],
            dropna=False,
        )
        .agg(
            relationship_rows=("older_code", "size"),
            distinct_older_codes=("older_code", "nunique"),
        )
        .reset_index()
        .sort_values(
            ["newer_code", "ex_marker_clean", "relationship"]
        )
    )

    marker_summary.to_csv(
        OUTPUT_MARKER,
        index=False,
        encoding="utf-8-sig",
    )

    # Preserve all rows that do not have an EX marker.
    non_ex = df[~df["is_ex"]].copy()

    non_ex.to_csv(
        OUTPUT_EXCEPTIONS,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Total source rows: {len(df):,}")
    print(f"Distinct newer codes: {df['newer_code'].nunique():,}")
    print(f"EX-marked rows: {df['is_ex'].sum():,}")
    print(f"Non-EX rows: {len(non_ex):,}")
    print()

    print("CHAPTER DISTRIBUTION")
    for code in TARGET_CODES:
        subset = chapter_summary[
            chapter_summary["newer_code"] == code
        ]

        parts = [
            f"Ch {row['older_chapter']}: {row['relationship_rows']}"
            for _, row in subset.iterrows()
        ]

        same_chapter = df[
            (df["newer_code"] == code)
            & df["is_same_chapter"]
        ].shape[0]

        cross_chapter = df[
            (df["newer_code"] == code)
            & ~df["is_same_chapter"]
        ].shape[0]

        print(
            f"HS2017 {code} | "
            f"same-chapter={same_chapter} | "
            f"cross-chapter={cross_chapter} | "
            + "; ".join(parts)
        )

    print()
    print("NON-EX SOURCE ROWS")

    if non_ex.empty:
        print("No non-EX rows found.")
    else:
        for _, row in non_ex.iterrows():
            print(
                f"HS2017 {row['newer_code']} | "
                f"HS2012 {row['older_code']} | "
                f"chapter={row['older_chapter']} | "
                f"relationship={row['relationship']}"
            )

    print()
    print("OUTPUT FILES")
    print(OUTPUT_CHAPTER)
    print(OUTPUT_MARKER)
    print(OUTPUT_EXCEPTIONS)
    print("\nPHASE 37 COMPLETED")


if __name__ == "__main__":
    main()
