
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT_FILE = AGG / "41_shared_mappings_with_hs2012_descriptions.csv"

OUTPUT_CHAPTERS = AGG / "42_shared_hs2012_chapter_profile.csv"
OUTPUT_CODES = AGG / "42_shared_hs2012_code_profile.csv"


def main():
    print("\nPHASE 42 - PROFILE SHARED HS2012 CHAPTERS")
    print("-" * 46)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(
        INPUT_FILE,
        dtype="string",
        keep_default_na=False,
    )

    required = [
        "older_code",
        "description",
        "description_found",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Use unique older HS2012 codes, not 474 repeated rows.
    codes = df[
        ["older_code", "description", "description_found"]
    ].drop_duplicates()

    codes["older_code"] = codes["older_code"].str.strip()
    codes["chapter"] = codes["older_code"].str[:2]

    codes["description_found"] = (
        codes["description_found"].str.lower().eq("true")
    )

    invalid = codes[
        ~codes["older_code"].str.fullmatch(r"\d{6}")
    ]

    if not invalid.empty:
        print(
            f"WARNING: {len(invalid)} codes are not six-digit numeric codes."
        )

    chapter_profile = (
        codes.groupby("chapter", dropna=False)
        .agg(
            distinct_hs2012_codes=("older_code", "nunique"),
            descriptions_available=("description_found", "sum"),
        )
        .reset_index()
        .sort_values(
            "distinct_hs2012_codes",
            ascending=False,
        )
    )

    total_codes = codes["older_code"].nunique()

    chapter_profile["share_of_158_codes_pct"] = (
        chapter_profile["distinct_hs2012_codes"]
        / total_codes
        * 100
    ).round(2)

    codes = codes.sort_values(
        ["chapter", "older_code"]
    )

    chapter_profile.to_csv(OUTPUT_CHAPTERS, index=False)
    codes.to_csv(OUTPUT_CODES, index=False)

    print(f"Distinct HS2012 codes: {total_codes}")
    print(f"HS2012 chapters represented: {len(chapter_profile)}")

    print("\nCHAPTER PROFILE")
    print(chapter_profile.to_string(index=False))

    print("\nOUTPUT FILES")
    print(OUTPUT_CHAPTERS)
    print(OUTPUT_CODES)

    print("\nPHASE 42 COMPLETED")


if __name__ == "__main__":
    main()
