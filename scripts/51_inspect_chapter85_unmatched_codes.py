
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT = AGG / "50_chapter85_manual_review_batch.csv"
OUT = AGG / "51_chapter85_unmatched_description_report.txt"

def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    df = pd.read_csv(INPUT, dtype=str).fillna("")

    required = [
        "hs2012_code",
        "hs2012_description",
        "manual_review_group",
        "hs2017_target_codes",
        "source_relationship_labels",
        "matched_keywords",
    ]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    unmatched = df[
        df["manual_review_group"] == "1 - No keyword match"
    ].copy()

    unmatched = unmatched.sort_values("hs2012_code")

    lines = [
        "PHASE 51 — CHAPTER 85 UNMATCHED DESCRIPTION REVIEW",
        f"Unmatched codes: {len(unmatched)}",
        "",
    ]

    for _, row in unmatched.iterrows():
        lines.extend([
            f"HS2012 CODE: {row['hs2012_code']}",
            f"DESCRIPTION: {row['hs2012_description']}",
            f"HS2017 TARGETS: {row['hs2017_target_codes']}",
            f"RELATIONSHIP: {row['source_relationship_labels']}",
            f"KEYWORD HITS: {row['matched_keywords'] or 'None'}",
            "-" * 72,
            "",
        ])

    OUT.write_text("\n".join(lines), encoding="utf-8")

    print("Phase 51 completed.")
    print("Unmatched Chapter 85 codes:", len(unmatched))
    print("Report:", OUT)
    print("\n".join(lines))

if __name__ == "__main__":
    main()
