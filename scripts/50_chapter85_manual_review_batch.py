
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

QUEUE = AGG / "48_hs2012_manual_review_queue.csv"
CHAPTER_PROFILE = AGG / "49_hs2012_chapter_review_profile.csv"

OUT = AGG / "50_chapter85_manual_review_batch.csv"
SUMMARY = AGG / "50_chapter85_manual_review_summary.txt"

def main():
    if not QUEUE.exists():
        raise FileNotFoundError(QUEUE)
    if not CHAPTER_PROFILE.exists():
        raise FileNotFoundError(CHAPTER_PROFILE)

    queue = pd.read_csv(QUEUE, dtype=str).fillna("")
    chapter_profile = pd.read_csv(
        CHAPTER_PROFILE, dtype=str
    ).fillna("")

    required = [
        "hs2012_code",
        "hs2012_description",
        "manual_review_group",
        "exploratory_family_tags",
        "matched_keywords",
        "review_decision",
        "reviewed_product_scope",
        "reviewer_notes",
    ]

    missing = [col for col in required if col not in queue.columns]
    if missing:
        raise ValueError(
            f"Missing queue columns: {missing}. "
            f"Available: {list(queue.columns)}"
        )

    queue["hs2012_code_clean"] = (
        queue["hs2012_code"].astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )

    # Chapter 85 codes begin with 85.
    chapter85 = queue[
        queue["hs2012_code_clean"].str.startswith("85")
    ].copy()

    if chapter85.empty:
        raise ValueError("No HS2012 Chapter 85 codes found.")

    group_order = {
        "1 - No keyword match": 1,
        "2 - Multiple keyword matches": 2,
        "3 - Single keyword match": 3,
    }

    chapter85["review_group_order"] = (
        chapter85["manual_review_group"].map(group_order).fillna(9)
    )

    chapter85 = chapter85.sort_values(
        ["review_group_order", "hs2012_code_clean"]
    )

    chapter85["review_batch"] = "Chapter 85"
    chapter85["review_batch_note"] = (
        "Manual description review; keyword tags are exploratory "
        "and do not establish exact ex scope."
    )

    chapter85.to_csv(OUT, index=False)

    counts = chapter85["manual_review_group"].value_counts().to_dict()

    lines = [
        "PHASE 50 — CHAPTER 85 MANUAL REVIEW BATCH",
        f"Total Chapter 85 codes: {len(chapter85):,}",
        f"No keyword match: "
        f"{counts.get('1 - No keyword match', 0):,}",
        f"Multiple keyword matches: "
        f"{counts.get('2 - Multiple keyword matches', 0):,}",
        f"Single keyword match: "
        f"{counts.get('3 - Single keyword match', 0):,}",
        "",
        "Review order:",
        "1. No keyword match",
        "2. Multiple keyword matches",
        "3. Single keyword match",
        "",
        "Caution:",
        "Chapter 85 membership does not prove semiconductor relevance.",
        "The source mappings are ex partial-scope relationships.",
        "Do not allocate trade values from these mappings.",
        "",
        f"Batch file: {OUT}",
    ]

    SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    print("\nPhase 50 completed.")
    print("Chapter 85 codes:", len(chapter85))
    print("No keyword match:", counts.get(
        "1 - No keyword match", 0
    ))
    print("Multiple matches:", counts.get(
        "2 - Multiple keyword matches", 0
    ))
    print("Single match:", counts.get(
        "3 - Single keyword match", 0
    ))
    print("Output:", OUT)
    print("Summary:", SUMMARY)
    print("\n".join(lines))

if __name__ == "__main__":
    main()
