
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT = AGG / "47_hs2012_product_family_review.csv"
OUT_QUEUE = AGG / "48_hs2012_manual_review_queue.csv"
OUT_SUMMARY = AGG / "48_hs2012_manual_review_queue_summary.txt"

def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    df = pd.read_csv(INPUT, dtype=str).fillna("")

    required = [
        "hs2012_code",
        "hs2012_description",
        "hs2017_target_codes",
        "has_ex_relationship",
        "source_relationship_labels",
        "exploratory_family_tags",
        "matched_keywords",
        "keyword_family_count",
        "review_priority",
    ]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    df["keyword_family_count_num"] = pd.to_numeric(
        df["keyword_family_count"], errors="coerce"
    ).fillna(0).astype(int)

    def review_group(count):
        if count == 0:
            return "1 - No keyword match"
        if count > 1:
            return "2 - Multiple keyword matches"
        return "3 - Single keyword match"

    df["manual_review_group"] = df[
        "keyword_family_count_num"
    ].apply(review_group)

    df["manual_review_reason"] = df[
        "keyword_family_count_num"
    ].apply(
        lambda count: (
            "Description not captured by current keyword rules; "
            "inspect official description and source context."
            if count == 0 else
            "Description matched several broad keyword families; "
            "review category overlap."
            if count > 1 else
            "One exploratory keyword family matched; verify manually."
        )
    )

    df["review_decision"] = ""
    df["reviewed_product_scope"] = ""
    df["reviewer_notes"] = ""

    # Prioritize unmatched and ambiguous descriptions.
    df = df.sort_values(
        by=[
            "keyword_family_count_num",
            "hs2012_code",
        ],
        ascending=[True, True],
    )

    # Keep useful review fields plus the original audit fields.
    df.to_csv(OUT_QUEUE, index=False)

    group_counts = (
        df["manual_review_group"].value_counts().to_dict()
    )

    lines = [
        "PHASE 48 — HS2012 MANUAL REVIEW QUEUE",
        f"Total HS2012 codes: {len(df):,}",
        "",
        "Review groups:",
        f"No keyword match: "
        f"{group_counts.get('1 - No keyword match', 0):,}",
        f"Multiple keyword matches: "
        f"{group_counts.get('2 - Multiple keyword matches', 0):,}",
        f"Single keyword match: "
        f"{group_counts.get('3 - Single keyword match', 0):,}",
        "",
        "First 20 codes in review queue:",
    ]

    for _, row in df.head(20).iterrows():
        lines.append(
            f"{row['hs2012_code']} | "
            f"{row['hs2012_description']} | "
            f"{row['manual_review_group']} | "
            f"Tags: {row['exploratory_family_tags'] or 'none'}"
        )

    lines += [
        "",
        "Review guidance:",
        "Use the official HS2012 description and original source row.",
        "Do not infer exact ex scope from the description alone.",
        "Do not allocate trade values to HS2017 targets based on",
        "keyword tags or this review queue.",
        "",
        f"Queue file: {OUT_QUEUE}",
    ]

    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    print("\nPhase 48 completed.")
    print("Total codes:", len(df))
    print("No keyword match:", group_counts.get(
        "1 - No keyword match", 0
    ))
    print("Multiple matches:", group_counts.get(
        "2 - Multiple keyword matches", 0
    ))
    print("Single match:", group_counts.get(
        "3 - Single keyword match", 0
    ))
    print("Queue:", OUT_QUEUE)
    print("Summary:", OUT_SUMMARY)
    print("\n".join(lines))

if __name__ == "__main__":
    main()
