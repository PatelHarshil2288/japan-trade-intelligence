from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
DATA = ROOT / "data" / "processed" / "aggregated"

RELATIONSHIPS = DATA / "22_hs_concordance_relationships.csv"
CLASSIFICATIONS = DATA / "22_hs_classification_codes.csv"

TARGET_CODES = ["854231", "854232", "854239"]

print("=" * 80)
print("PHASE 5.11 — COMPARE HIGH-DEGREE HS2017 LINK SETS")
print("=" * 80)

rel = pd.read_csv(
    RELATIONSHIPS,
    dtype=str,
    low_memory=False
)

classes = pd.read_csv(
    CLASSIFICATIONS,
    dtype=str,
    low_memory=False
)

links = rel[
    (rel["newer_edition"] == "2017")
    & (rel["older_edition"] == "2012")
    & (rel["newer_code"].isin(TARGET_CODES))
].copy()

# Build one set of linked HS2012 codes per HS2017 code
code_sets = {
    code: set(
        links.loc[
            links["newer_code"] == code,
            "older_code"
        ].dropna()
    )
    for code in TARGET_CODES
}

print("\nLINK SET SIZES")
for code, codes in code_sets.items():
    print(f"HS2017 {code}: {len(codes)} HS2012 codes")

print("\nPAIRWISE SET COMPARISON")

for i in range(len(TARGET_CODES)):
    for j in range(i + 1, len(TARGET_CODES)):
        a = TARGET_CODES[i]
        b = TARGET_CODES[j]

        intersection = code_sets[a] & code_sets[b]
        only_a = code_sets[a] - code_sets[b]
        only_b = code_sets[b] - code_sets[a]

        print(f"\n{a} vs {b}")
        print("Shared codes:", len(intersection))
        print(f"Only in {a}:", len(only_a))
        print(f"Only in {b}:", len(only_b))
        print(
            "Jaccard similarity:",
            round(
                len(intersection) / len(code_sets[a] | code_sets[b]),
                6
            ) if code_sets[a] | code_sets[b] else 0
        )

# HS2012 descriptions
hs2012 = classes[
    classes["hs_edition"] == "2012"
][["hs6_code", "description"]].copy()

hs2012 = hs2012.rename(columns={
    "hs6_code": "older_code",
    "description": "older_description"
})

# Inspect up to 30 linked codes in sorted order
all_codes = sorted(set.union(*code_sets.values()))

sample = pd.DataFrame({
    "older_code": all_codes[:30]
})

sample = sample.merge(
    hs2012,
    on="older_code",
    how="left",
    validate="one_to_one"
)

print("\nFIRST 30 LINKED HS2012 CODES AND DESCRIPTIONS")
print(sample.to_string(index=False))

# Save the sample and exact-set comparison
sample_path = DATA / "31_high_degree_link_description_sample.csv"
sample.to_csv(
    sample_path,
    index=False,
    encoding="utf-8-sig"
)

comparison_rows = []

for code in TARGET_CODES:
    comparison_rows.append({
        "hs2017_code": code,
        "linked_hs2012_count": len(code_sets[code]),
        "linked_hs2012_codes": ";".join(sorted(code_sets[code]))
    })

comparison_path = DATA / "31_high_degree_link_set_comparison.csv"
pd.DataFrame(comparison_rows).to_csv(
    comparison_path,
    index=False,
    encoding="utf-8-sig"
)

print("\nOUTPUT FILES")
print(sample_path)
print(comparison_path)

print("\n" + "=" * 80)
print("PHASE 5.11 COMPLETED")
print("=" * 80)