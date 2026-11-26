
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT_FILE = AGG / "43_shared_hs2012_product_description_catalogue.csv"

OUTPUT_CSV = AGG / "44_shared_hs2012_description_review.csv"
OUTPUT_TXT = AGG / "44_shared_hs2012_descriptions_by_chapter.txt"


def main():
    print("\nPHASE 44 - REVIEW HS2012 PRODUCT DESCRIPTIONS")
    print("-" * 48)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(
        INPUT_FILE,
        dtype="string",
        keep_default_na=False,
    )

    required = ["older_code", "chapter", "description"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df = (
        df[required]
        .drop_duplicates()
        .sort_values(["chapter", "older_code"])
        .copy()
    )

    df["chapter"] = df["chapter"].str.zfill(2)
    df["older_code"] = df["older_code"].str.zfill(6)

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    with open(OUTPUT_TXT, "w", encoding="utf-8") as file:
        file.write(
            "HS2012 DESCRIPTIONS IN SHARED HS2017 EX CORRELATIONS\n"
        )
        file.write("=" * 58 + "\n\n")

        for chapter, chapter_df in df.groupby("chapter", sort=True):
            file.write(
                f"\nCHAPTER {chapter} "
                f"({len(chapter_df)} distinct codes)\n"
            )
            file.write("-" * 58 + "\n")

            for _, row in chapter_df.iterrows():
                file.write(
                    f"{row['older_code']} | {row['description']}\n"
                )

    chapter_counts = (
        df.groupby("chapter")
        .agg(distinct_codes=("older_code", "nunique"))
        .reset_index()
        .sort_values("chapter")
    )

    print(f"Distinct HS2012 codes: {df['older_code'].nunique()}")
    print(f"Chapters: {df['chapter'].nunique()}")

    print("\nCODES BY CHAPTER")
    print(chapter_counts.to_string(index=False))

    print("\nOUTPUT FILES")
    print(OUTPUT_CSV)
    print(OUTPUT_TXT)

    print("\nPHASE 44 COMPLETED")


if __name__ == "__main__":
    main()
