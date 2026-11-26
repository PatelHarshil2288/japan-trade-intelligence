from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
DATA = ROOT / "data" / "processed" / "aggregated"

RELATIONSHIPS = DATA / "22_hs_concordance_relationships.csv"
CLASSIFICATIONS = DATA / "22_hs_classification_codes.csv"

TARGET_CODES = ["854231", "854232", "854239"]

print("=" * 80)
print("PHASE 5.10 — PROFILE HS2017 HIGH-DEGREE CODE LINKS")
print("=" * 80)

relationships = pd.read_csv(
    RELATIONSHIPS,
    dtype=str,
    low_memory=False
)

classifications = pd.read_csv(
    CLASSIFICATIONS,
    dtype=str,
    low_memory=False
)

# HS2017 -> HS2012 relationships for target codes
links = relationships[
    (relationships["newer_edition"] == "2017")
    & (relationships["older_edition"] == "2012")
    & (relationships["newer_code"].isin(TARGET_CODES))
].copy()

# Prepare HS2012 descriptions
hs2012 = classifications[
    classifications["hs_edition"] == "2012"
][["hs6_code", "description"]].copy()

hs2012 = hs2012.rename(columns={
    "hs6_code": "older_code",
    "description": "older_description"
})

# Join descriptions to relationship rows
links = links.merge(
    hs2012,
    on="older_code",
    how="left",
    validate="many_to_one"
)

links = links.sort_values(
    ["newer_code", "older_code"]
)

detail_path = DATA / "30_hs2017_high_degree_links_with_descriptions.csv"

links.to_csv(
    detail_path,
    index=False,
    encoding="utf-8-sig"
)

# Summary by target code
summary = (
    links.groupby("newer_code", dropna=False)
    .agg(
        relationship_rows=("older_code", "size"),
        unique_hs2012_codes=("older_code", "nunique"),
        missing_descriptions=("older_description", lambda x: x.isna().sum()),
        relationship_types=("relationship", lambda x: "; ".join(sorted(x.dropna().unique()))),
        ex_markers=("ex_marker", lambda x: "; ".join(sorted(x.dropna().unique()))),
    )
    .reset_index()
)

summary_path = DATA / "30_hs2017_high_degree_link_summary.csv"

summary.to_csv(
    summary_path,
    index=False,
    encoding="utf-8-sig"
)

# Group linked older codes by HS chapter (first two digits)
links["hs2012_chapter"] = links["older_code"].str[:2]

chapter_summary = (
    links.groupby(
        ["newer_code", "hs2012_chapter"],
        dropna=False
    )
    .agg(
        relationship_rows=("older_code", "size"),
        unique_hs2012_codes=("older_code", "nunique")
    )
    .reset_index()
    .sort_values(
        ["newer_code", "relationship_rows"],
        ascending=[True, False]
    )
)

chapter_path = DATA / "30_hs2017_high_degree_chapter_profile.csv"

chapter_summary.to_csv(
    chapter_path,
    index=False,
    encoding="utf-8-sig"
)

print("\nSUMMARY BY HS2017 CODE")
print(summary.to_string(index=False))

print("\nLINKED HS2012 CODES BY CHAPTER")
print(chapter_summary.to_string(index=False))

print("\nOUTPUT FILES")
print(detail_path)
print(summary_path)
print(chapter_path)

print("\n" + "=" * 80)
print("PHASE 5.10 COMPLETED")
print("=" * 80)