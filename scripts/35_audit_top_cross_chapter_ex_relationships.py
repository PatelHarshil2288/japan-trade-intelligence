
from pathlib import Path
import pandas as pd

# ------------------------------------------------------------
# Phase 35: Audit top-ranked cross-chapter EX relationships
# ------------------------------------------------------------

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

RANKING_FILE = AGG / "34_cross_chapter_ex_code_rankings.csv"
RELATIONSHIP_FILE = AGG / "33_ex_cross_chapter_relationships_for_review.csv"
CLASSIFICATION_FILE = AGG / "22_hs_classification_codes.csv"

OUTPUT_DETAIL = AGG / "35_top_cross_chapter_ex_relationship_details.csv"
OUTPUT_SUMMARY = AGG / "35_top_cross_chapter_ex_relationship_summary.csv"

TOP_N_CODES = 20


def require_columns(df, required, filename):
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"\nMissing columns in {filename}: {missing}"
            f"\nAvailable columns: {list(df.columns)}"
        )


def normalize_code(series):
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )


def compact(value, limit=100):
    if pd.isna(value):
        return ""
    value = " ".join(str(value).split())
    if len(value) > limit:
        return value[: limit - 3] + "..."
    return value


def main():
    print("\nPHASE 35 - TOP CROSS-CHAPTER EX RELATIONSHIP AUDIT")
    print("-" * 54)

    for file in [RANKING_FILE, RELATIONSHIP_FILE, CLASSIFICATION_FILE]:
        if not file.exists():
            raise FileNotFoundError(f"File not found:\n{file}")

    ranking = pd.read_csv(RANKING_FILE, dtype="string")
    relationships = pd.read_csv(RELATIONSHIP_FILE, dtype="string")
    classifications = pd.read_csv(CLASSIFICATION_FILE, dtype="string")

    require_columns(
        ranking,
        ["rank", "newer_edition", "newer_code"],
        RANKING_FILE.name,
    )

    require_columns(
        relationships,
        [
            "newer_edition",
            "newer_code",
            "older_edition",
            "older_code",
            "relationship",
        ],
        RELATIONSHIP_FILE.name,
    )

    require_columns(
        classifications,
        ["hs_edition", "hs6_code", "description"],
        CLASSIFICATION_FILE.name,
    )

    # Normalize HS codes.
    ranking["newer_code"] = normalize_code(ranking["newer_code"])
    relationships["newer_code"] = normalize_code(
        relationships["newer_code"]
    )
    relationships["older_code"] = normalize_code(
        relationships["older_code"]
    )
    classifications["hs6_code"] = normalize_code(
        classifications["hs6_code"]
    )

    # Select the highest-ranked newer HS codes.
    top_codes = ranking.head(TOP_N_CODES)[
        ["rank", "newer_edition", "newer_code"]
    ].copy()

    top_codes["rank"] = pd.to_numeric(
        top_codes["rank"], errors="coerce"
    )

    # Preserve all original relationship rows for selected codes.
    detail = relationships.merge(
        top_codes,
        on=["newer_edition", "newer_code"],
        how="inner",
    )

    if detail.empty:
        raise ValueError(
            "No relationship rows matched the top-ranked codes."
        )

    # Add newer and older code descriptions.
    descriptions = classifications[
        ["hs_edition", "hs6_code", "description"]
    ].drop_duplicates()

    newer_desc = descriptions.rename(
        columns={
            "hs_edition": "newer_edition",
            "hs6_code": "newer_code",
            "description": "newer_description",
        }
    )

    older_desc = descriptions.rename(
        columns={
            "hs_edition": "older_edition",
            "hs6_code": "older_code",
            "description": "older_description",
        }
    )

    detail = detail.merge(
        newer_desc,
        on=["newer_edition", "newer_code"],
        how="left",
    )

    detail = detail.merge(
        older_desc,
        on=["older_edition", "older_code"],
        how="left",
    )

    detail["newer_chapter"] = detail["newer_code"].str[:2]
    detail["older_chapter"] = detail["older_code"].str[:2]

    detail["is_cross_chapter"] = (
        detail["newer_chapter"] != detail["older_chapter"]
    )

    # Put key columns first, retaining all original source columns.
    preferred = [
        "rank",
        "newer_edition",
        "newer_code",
        "newer_description",
        "newer_chapter",
        "ex_marker",
        "older_edition",
        "older_code",
        "older_description",
        "older_chapter",
        "relationship",
        "source_file",
        "source_sheet",
        "is_cross_chapter",
    ]

    ordered = [col for col in preferred if col in detail.columns]
    remaining = [col for col in detail.columns if col not in ordered]
    detail = detail[ordered + remaining]

    detail = detail.sort_values(
        ["rank", "older_code"],
        kind="stable",
    ).reset_index(drop=True)

    # Summary by newer HS code.
    summary = (
        detail.groupby(
            [
                "rank",
                "newer_edition",
                "newer_code",
                "newer_description",
            ],
            dropna=False,
        )
        .agg(
            relationship_rows=("older_code", "size"),
            distinct_older_codes=("older_code", "nunique"),
            distinct_older_chapters=("older_chapter", "nunique"),
            older_chapters=(
                "older_chapter",
                lambda x: ", ".join(sorted(set(x.dropna()))),
            ),
        )
        .reset_index()
        .sort_values("rank")
    )

    # Save complete detail and summary.
    detail.to_csv(
        OUTPUT_DETAIL,
        index=False,
        encoding="utf-8-sig",
    )

    summary.to_csv(
        OUTPUT_SUMMARY,
        index=False,
        encoding="utf-8-sig",
    )

    # Compact console results.
    missing_newer = detail["newer_description"].isna().sum()
    missing_older = detail["older_description"].isna().sum()

    print(f"Selected top codes: {len(top_codes):,}")
    print(f"Relationship rows extracted: {len(detail):,}")
    print(f"Missing newer descriptions: {missing_newer:,}")
    print(f"Missing older descriptions: {missing_older:,}")
    print()

    print("SUMMARY BY NEWER HS CODE")
    for _, row in summary.iterrows():
        code = row["newer_code"]
        edition = row["newer_edition"]
        rows = row["relationship_rows"]
        old_codes = row["distinct_older_codes"]
        chapters = row["older_chapters"]

        print(
            f"Rank {int(row['rank']):>2} | "
            f"HS{edition} {code} | "
            f"rows={rows} | "
            f"older_codes={old_codes} | "
            f"chapters={chapters}"
        )

    print("\nOUTPUT FILES")
    print(OUTPUT_DETAIL)
    print(OUTPUT_SUMMARY)

    print("\nPHASE 35 COMPLETED")


if __name__ == "__main__":
    main()
