
from pathlib import Path
from collections import Counter
import re
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT_FILE = AGG / "42_shared_hs2012_code_profile.csv"

OUTPUT_CATALOGUE = AGG / "43_shared_hs2012_product_description_catalogue.csv"
OUTPUT_KEYWORDS = AGG / "43_shared_hs2012_description_keyword_frequency.csv"
OUTPUT_SUMMARY = AGG / "43_shared_hs2012_description_profile_summary.csv"

STOPWORDS = {
    "other", "parts", "thereof", "including", "whether",
    "not", "elsewhere", "specified", "provided", "for",
    "with", "without", "and", "the", "of", "or", "in",
    "to", "by", "from", "than", "which", "that", "such",
    "these", "those", "their", "having", "used", "use",
    "goods", "articles", "products", "machines", "machine",
    "apparatus", "equipment", "parts", "accessories",
    "heading", "subheading", "nes", "n.e.s", "nesoi",
}


def extract_terms(description):
    text = str(description).lower()
    tokens = re.findall(r"[a-z]{4,}", text)

    return {
        token for token in tokens
        if token not in STOPWORDS
    }


def main():
    print("\nPHASE 43 - HS2012 PRODUCT DESCRIPTION PROFILE")
    print("-" * 48)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(
        INPUT_FILE,
        dtype="string",
        keep_default_na=False,
    )

    required = ["older_code", "description", "chapter"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Ensure one record per HS2012 code.
    catalogue = (
        df[["older_code", "chapter", "description"]]
        .drop_duplicates()
        .sort_values(["chapter", "older_code"])
        .copy()
    )

    catalogue["description"] = (
        catalogue["description"].str.strip()
    )

    catalogue["description_word_count"] = (
        catalogue["description"]
        .str.findall(r"\b[A-Za-z]+\b")
        .str.len()
    )

    catalogue.to_csv(OUTPUT_CATALOGUE, index=False)

    keyword_rows = []

    for chapter, chapter_df in catalogue.groupby("chapter"):
        term_counts = Counter()

        for description in chapter_df["description"]:
            terms = extract_terms(description)
            term_counts.update(terms)

        for term, count in term_counts.most_common():
            keyword_rows.append({
                "chapter": chapter,
                "keyword": term,
                "description_count": count,
                "chapter_code_count": len(chapter_df),
                "share_of_chapter_codes_pct": round(
                    count / len(chapter_df) * 100,
                    2,
                ),
            })

    keywords = pd.DataFrame(keyword_rows)

    if not keywords.empty:
        keywords = keywords.sort_values(
            ["chapter", "description_count", "keyword"],
            ascending=[True, False, True],
        )

    keywords.to_csv(OUTPUT_KEYWORDS, index=False)

    summary = (
        catalogue.groupby("chapter")
        .agg(
            distinct_hs2012_codes=("older_code", "nunique"),
            descriptions=("description", "nunique"),
            average_description_words=(
                "description_word_count", "mean"
            ),
        )
        .reset_index()
    )

    summary["average_description_words"] = (
        summary["average_description_words"].round(2)
    )

    summary.to_csv(OUTPUT_SUMMARY, index=False)

    print(f"Unique HS2012 codes: {len(catalogue)}")
    print(f"Chapters profiled: {catalogue['chapter'].nunique()}")

    print("\nDESCRIPTION PROFILE BY CHAPTER")
    print(summary.to_string(index=False))

    print("\nTOP DESCRIPTION KEYWORDS BY CHAPTER")

    for chapter in sorted(catalogue["chapter"].unique()):
        top = keywords[keywords["chapter"] == chapter].head(12)

        print(f"\nChapter {chapter}")
        if top.empty:
            print("No keywords extracted.")
        else:
            print(
                top[["keyword", "description_count"]]
                .to_string(index=False)
            )

    print("\nOUTPUT FILES")
    print(OUTPUT_CATALOGUE)
    print(OUTPUT_KEYWORDS)
    print(OUTPUT_SUMMARY)

    print("\nPHASE 43 COMPLETED")


if __name__ == "__main__":
    main()
