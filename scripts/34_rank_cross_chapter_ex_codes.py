
from pathlib import Path
import pandas as pd

# ------------------------------------------------------------
# Phase 34: Rank cross-chapter EX HS concordance relationships
# ------------------------------------------------------------

ROOT = Path(r"D:\Japan_Trade_Intelligence")

AGG = ROOT / "data" / "processed" / "aggregated"

INPUT_FILE = AGG / "33_ex_cross_chapter_relationships_for_review.csv"
CLASSIFICATION_FILE = AGG / "22_hs_classification_codes.csv"

OUTPUT_RANKINGS = AGG / "34_cross_chapter_ex_code_rankings.csv"
OUTPUT_TOP100 = AGG / "34_top_100_cross_chapter_ex_codes.csv"

TOP_N = 100
DISPLAY_N = 20
DESCRIPTION_LIMIT = 75


def require_columns(df, required, filename):
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns in {filename}: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )


def clean_code(series):
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )


def short_text(value, limit=DESCRIPTION_LIMIT):
    if pd.isna(value):
        return ""
    value = " ".join(str(value).split())
    if len(value) > limit:
        return value[: limit - 3] + "..."
    return value


def print_compact_table(df, columns, limit=DISPLAY_N):
    """Print a compact table without wide pandas column padding."""
    if df.empty:
        print("No rows to display.")
        return

    display = df[columns].head(limit).copy()

    for col in display.columns:
        display[col] = display[col].map(short_text)

    widths = {
        col: min(
            max(len(col), *(len(str(v)) for v in display[col])),
            DESCRIPTION_LIMIT,
        )
        for col in columns
    }

    header = " | ".join(col.ljust(widths[col]) for col in columns)
    print(header)
    print("-" * min(len(header), 160))

    for _, row in display.iterrows():
        print(
            " | ".join(
                str(row[col])[:widths[col]].ljust(widths[col])
                for col in columns
            )
        )


def main():
    print("\nPHASE 34 - CROSS-CHAPTER EX MAPPING RANKING")
    print("-" * 48)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found:\n{INPUT_FILE}")

    if not CLASSIFICATION_FILE.exists():
        raise FileNotFoundError(
            f"Classification file not found:\n{CLASSIFICATION_FILE}"
        )

    relationships = pd.read_csv(
        INPUT_FILE,
        dtype="string",
        keep_default_na=False,
    )

    classification = pd.read_csv(
        CLASSIFICATION_FILE,
        dtype="string",
        keep_default_na=False,
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
        INPUT_FILE.name,
    )

    require_columns(
        classification,
        ["hs_edition", "hs6_code", "description"],
        CLASSIFICATION_FILE.name,
    )

    # Normalize HS codes and edition values.
    relationships["newer_code"] = clean_code(
        relationships["newer_code"]
    )
    relationships["older_code"] = clean_code(
        relationships["older_code"]
    )

    classification["hs6_code"] = clean_code(
        classification["hs6_code"]
    )

    relationships["newer_edition"] = (
        relationships["newer_edition"].str.strip()
    )
    relationships["older_edition"] = (
        relationships["older_edition"].str.strip()
    )
    classification["hs_edition"] = (
        classification["hs_edition"].str.strip()
    )

    # Derive chapters from the first two digits of each HS6 code.
    relationships["newer_chapter"] = (
        relationships["newer_code"].str[:2]
    )
    relationships["older_chapter"] = (
        relationships["older_code"].str[:2]
    )

    # Retain only cross-chapter relationships.
    cross_chapter = relationships[
        relationships["newer_chapter"]
        != relationships["older_chapter"]
    ].copy()

    if cross_chapter.empty:
        print("No cross-chapter relationships found.")
        return

    # Attach newer-code descriptions.
    newer_descriptions = classification[
        ["hs_edition", "hs6_code", "description"]
    ].drop_duplicates()

    newer_descriptions = newer_descriptions.rename(
        columns={
            "hs_edition": "newer_edition",
            "hs6_code": "newer_code",
            "description": "newer_description",
        }
    )

    cross_chapter = cross_chapter.merge(
        newer_descriptions,
        on=["newer_edition", "newer_code"],
        how="left",
    )

    # Attach older-code descriptions.
    older_descriptions = classification[
        ["hs_edition", "hs6_code", "description"]
    ].drop_duplicates()

    older_descriptions = older_descriptions.rename(
        columns={
            "hs_edition": "older_edition",
            "hs6_code": "older_code",
            "description": "older_description",
        }
    )

    cross_chapter = cross_chapter.merge(
        older_descriptions,
        on=["older_edition", "older_code"],
        how="left",
    )

    # Count distinct linked codes for each newer code.
    ranking = (
        cross_chapter.groupby(
            [
                "newer_edition",
                "newer_code",
                "newer_chapter",
                "newer_description",
            ],
            dropna=False,
        )
        .agg(
            cross_chapter_link_rows=("older_code", "size"),
            distinct_older_codes=("older_code", "nunique"),
            distinct_older_chapters=("older_chapter", "nunique"),
            older_chapters=(
                "older_chapter",
                lambda x: ", ".join(sorted(set(x.dropna()))),
            ),
        )
        .reset_index()
    )

    ranking = ranking.sort_values(
        [
            "cross_chapter_link_rows",
            "distinct_older_codes",
            "newer_edition",
            "newer_code",
        ],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)

    ranking.insert(0, "rank", range(1, len(ranking) + 1))

    # Save full data; descriptions are not truncated in the CSV.
    ranking.to_csv(OUTPUT_RANKINGS, index=False, encoding="utf-8-sig")

    top100 = ranking.head(TOP_N).copy()
    top100.to_csv(OUTPUT_TOP100, index=False, encoding="utf-8-sig")

    # Compact console report.
    missing_descriptions = ranking[
        ranking["newer_description"].isna()
        | (ranking["newer_description"] == "")
    ].shape[0]

    print(f"Relationship rows: {len(relationships):,}")
    print(f"Cross-chapter rows: {len(cross_chapter):,}")
    print(f"Distinct newer codes: {len(ranking):,}")
    print(f"Missing newer descriptions: {missing_descriptions:,}")
    print()

    print(f"TOP {min(DISPLAY_N, len(ranking))} CODES")
    print_compact_table(
        ranking,
        [
            "rank",
            "newer_edition",
            "newer_code",
            "cross_chapter_link_rows",
            "distinct_older_codes",
            "older_chapters",
            "newer_description",
        ],
    )

    print("\nOUTPUT FILES")
    print(OUTPUT_RANKINGS)
    print(OUTPUT_TOP100)
    print("\nPHASE 34 COMPLETED")


if __name__ == "__main__":
    main()
