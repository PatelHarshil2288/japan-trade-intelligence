
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

QUEUE = AGG / "48_hs2012_manual_review_queue.csv"
SOURCE = AGG / "45_original_shared_mapping_source_rows.csv"

OUT_CHAPTER = AGG / "49_hs2012_chapter_review_profile.csv"
OUT_FAMILY = AGG / "49_hs2012_chapter_family_profile.csv"
OUT_SUMMARY = AGG / "49_hs2012_chapter_review_summary.txt"

def normalize_code(series):
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )

def main():
    if not QUEUE.exists():
        raise FileNotFoundError(QUEUE)
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    queue = pd.read_csv(QUEUE, dtype=str).fillna("")
    source = pd.read_csv(SOURCE, dtype=str).fillna("")

    required_queue = [
        "hs2012_code",
        "manual_review_group",
        "exploratory_family_tags",
        "keyword_family_count",
    ]
    missing = [c for c in required_queue if c not in queue.columns]
    if missing:
        raise ValueError(
            f"Missing queue columns: {missing}. "
            f"Available: {list(queue.columns)}"
        )

    if "older_code" not in source.columns:
        raise ValueError(
            f"Missing older_code in source. Columns: {list(source.columns)}"
        )
    if "older_chapter" not in source.columns:
        raise ValueError(
            f"Missing older_chapter in source. Columns: {list(source.columns)}"
        )

    queue["hs2012_code_clean"] = normalize_code(queue["hs2012_code"])
    source["older_code_clean"] = normalize_code(source["older_code"])

    chapter_map = (
        source[["older_code_clean", "older_chapter"]]
        .drop_duplicates()
        .copy()
    )

    # Check that each older code maps to exactly one chapter.
    chapter_conflicts = (
        chapter_map.groupby("older_code_clean")["older_chapter"]
        .nunique()
    )
    conflicts = chapter_conflicts[chapter_conflicts > 1]

    if len(conflicts):
        raise ValueError(
            "Some HS2012 codes have conflicting chapter values: "
            f"{conflicts.to_dict()}"
        )

    chapter_map = chapter_map.drop_duplicates("older_code_clean")

    df = queue.merge(
        chapter_map,
        left_on="hs2012_code_clean",
        right_on="older_code_clean",
        how="left",
        validate="one_to_one",
    )

    missing_chapter = df["older_chapter"].astype(str).str.strip().eq("")
    if missing_chapter.any():
        codes = df.loc[missing_chapter, "hs2012_code"].tolist()
        raise ValueError(f"Chapter missing for HS2012 codes: {codes}")

    df["chapter"] = (
        df["older_chapter"].astype(str).str.strip().str.zfill(2)
    )

    # Chapter-level review group counts.
    chapter_profile = (
        df.groupby("chapter", dropna=False)
        .agg(
            hs2012_code_count=("hs2012_code", "nunique"),
            no_keyword_match_count=(
                "manual_review_group",
                lambda s: (s == "1 - No keyword match").sum()
            ),
            multiple_keyword_match_count=(
                "manual_review_group",
                lambda s: (s == "2 - Multiple keyword matches").sum()
            ),
            single_keyword_match_count=(
                "manual_review_group",
                lambda s: (s == "3 - Single keyword match").sum()
            ),
        )
        .reset_index()
    )

    chapter_profile["no_match_pct"] = (
        chapter_profile["no_keyword_match_count"]
        / chapter_profile["hs2012_code_count"] * 100
    ).round(2)

    chapter_profile["multiple_match_pct"] = (
        chapter_profile["multiple_keyword_match_count"]
        / chapter_profile["hs2012_code_count"] * 100
    ).round(2)

    chapter_profile = chapter_profile.sort_values(
        ["hs2012_code_count", "chapter"],
        ascending=[False, True],
    )
    chapter_profile.to_csv(OUT_CHAPTER, index=False)

    # Long-form chapter × exploratory-family profile.
    family_rows = []

    for _, row in df.iterrows():
        tags = [
            tag.strip()
            for tag in row["exploratory_family_tags"].split(";")
            if tag.strip()
        ]

        if not tags:
            family_rows.append({
                "chapter": row["chapter"],
                "exploratory_family": "no_keyword_match",
                "hs2012_code": row["hs2012_code_clean"],
            })
        else:
            for tag in tags:
                family_rows.append({
                    "chapter": row["chapter"],
                    "exploratory_family": tag,
                    "hs2012_code": row["hs2012_code_clean"],
                })

    family_df = pd.DataFrame(family_rows)

    family_profile = (
        family_df.groupby(
            ["chapter", "exploratory_family"]
        )["hs2012_code"]
        .nunique()
        .reset_index(name="hs2012_code_count")
        .sort_values(
            ["chapter", "hs2012_code_count"],
            ascending=[True, False],
        )
    )
    family_profile.to_csv(OUT_FAMILY, index=False)

    lines = [
        "PHASE 49 — HS2012 CHAPTER REVIEW PROFILE",
        f"Total HS2012 codes: {df['hs2012_code'].nunique():,}",
        f"Distinct chapters: {df['chapter'].nunique():,}",
        "",
        "Chapter profile:",
    ]

    for _, row in chapter_profile.iterrows():
        lines.append(
            f"Chapter {row['chapter']}: "
            f"{int(row['hs2012_code_count'])} codes | "
            f"No keyword match: "
            f"{int(row['no_keyword_match_count'])} "
            f"({row['no_match_pct']}%) | "
            f"Multiple matches: "
            f"{int(row['multiple_keyword_match_count'])} "
            f"({row['multiple_match_pct']}%) | "
            f"Single match: "
            f"{int(row['single_keyword_match_count'])}"
        )

    lines += [
        "",
        "Interpretation caution:",
        "Counts describe the HS2012 code review workload only.",
        "Keyword tags are exploratory and do not establish exact ex scope.",
        "Do not interpret chapter counts as trade values or semiconductor",
        "product shares.",
        "",
        f"Chapter profile: {OUT_CHAPTER}",
        f"Chapter-family profile: {OUT_FAMILY}",
    ]

    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    print("\nPhase 49 completed.")
    print("Total codes:", df["hs2012_code"].nunique())
    print("Distinct chapters:", df["chapter"].nunique())
    print("Chapter profile:", OUT_CHAPTER)
    print("Family profile:", OUT_FAMILY)
    print("Summary:", OUT_SUMMARY)
    print("\n".join(lines))

if __name__ == "__main__":
    main()
