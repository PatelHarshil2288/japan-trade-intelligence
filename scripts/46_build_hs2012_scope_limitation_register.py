
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

SOURCE = AGG / "45_original_shared_mapping_source_rows.csv"
DESCRIPTIONS = AGG / "41_shared_mappings_with_hs2012_descriptions.csv"

OUT = AGG / "46_hs2012_scope_limitation_register.csv"
SUMMARY = AGG / "46_hs2012_scope_limitation_summary.txt"

TARGET_CODES = {"854231", "854232", "854239"}

def find_column(df, candidates):
    lookup = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None

def clean_code(series):
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    if not DESCRIPTIONS.exists():
        raise FileNotFoundError(DESCRIPTIONS)

    source = pd.read_csv(SOURCE, dtype=str).fillna("")
    descriptions = pd.read_csv(DESCRIPTIONS, dtype=str).fillna("")

    newer_col = find_column(source, ["newer_code"])
    older_col = find_column(source, ["older_code"])
    ex_col = find_column(source, ["ex_marker"])
    rel_col = find_column(source, ["relationship"])
    desc_col = find_column(source, ["older_description"])

    required = {
        "newer_code": newer_col,
        "older_code": older_col,
        "ex_marker": ex_col,
        "relationship": rel_col,
        "older_description": desc_col,
    }
    missing = [name for name, col in required.items() if col is None]
    if missing:
        raise ValueError(
            f"Missing required source columns: {missing}. "
            f"Available: {list(source.columns)}"
        )

    source["newer_code_clean"] = clean_code(source[newer_col])
    source["older_code_clean"] = clean_code(source[older_col])

    # Keep only the three target HS2017 codes.
    source = source[source["newer_code_clean"].isin(TARGET_CODES)].copy()

    # Limit to the 158 older codes present in the shared Phase 40 mapping set.
    older_desc_col = find_column(
        descriptions,
        ["older_code", "hs2012_code", "hs2012", "hs12_code"]
    )
    if older_desc_col is None:
        raise ValueError(
            "Could not find HS2012 code in Phase 41 descriptions file. "
            f"Columns: {list(descriptions.columns)}"
        )

    descriptions["older_code_clean"] = clean_code(descriptions[older_desc_col])
    shared_codes = set(descriptions["older_code_clean"])

    source = source[source["older_code_clean"].isin(shared_codes)].copy()

    # Use the official description already joined in Phase 41 when available.
    phase41_desc_col = find_column(
        descriptions,
        ["older_description", "description", "hs2012_description"]
    )

    description_map = {}
    if phase41_desc_col:
        description_map = (
            descriptions.drop_duplicates("older_code_clean")
            .set_index("older_code_clean")[phase41_desc_col]
            .to_dict()
        )

    rows = []

    for older_code, group in source.groupby("older_code_clean", sort=True):
        target_codes = sorted(set(group["newer_code_clean"]))
        markers = sorted(set(group[ex_col].astype(str).str.strip()))
        relationships = sorted(
            set(group[rel_col].astype(str).str.strip())
        )

        source_description = (
            group[desc_col].astype(str).str.strip()
            .replace("", pd.NA).dropna()
        )
        description = description_map.get(older_code, "")
        if not description and not source_description.empty:
            description = source_description.iloc[0]

        rows.append({
            "hs2012_code": older_code,
            "hs2012_description": description,
            "hs2017_target_codes": ";".join(target_codes),
            "target_code_count": len(target_codes),
            "source_mapping_row_count": len(group),
            "source_ex_markers": ";".join(markers),
            "source_relationship_labels": ";".join(relationships),
            "has_ex_relationship": any(
                marker.lower() == "ex" for marker in markers
            ),
            "whole_code_equivalence_claimed": False,
            "scope_warning": (
                "Partial-scope relationship: do not treat all trade "
                "under this HS2012 code as equivalent to the HS2017 "
                "target code."
            ),
            "review_status": "Needs product-scope review",
            "product_family_review": "",
            "review_notes": "",
        })

    register = pd.DataFrame(rows)
    register = register.sort_values("hs2012_code")
    register.to_csv(OUT, index=False)

    marker_counts = (
        register["has_ex_relationship"].value_counts().to_dict()
    )
    target_counts = (
        source.groupby("newer_code_clean")["older_code_clean"]
        .nunique().to_dict()
    )

    lines = [
        "PHASE 46 — HS2012 SCOPE-LIMITATION REGISTER",
        f"Register rows: {len(register):,}",
        f"Distinct HS2012 codes: {register['hs2012_code'].nunique():,}",
        f"Rows with ex relationship: {marker_counts.get(True, 0):,}",
        f"Rows without ex relationship: {marker_counts.get(False, 0):,}",
        "",
        "Distinct older HS2012 codes by HS2017 target:",
    ]

    for target in sorted(TARGET_CODES):
        lines.append(
            f"{target}: {target_counts.get(target, 0):,}"
        )

    lines += [
        "",
        "Interpretation:",
        "This register records source concordance relationships.",
        "It does not establish that all goods under an older HS2012",
        "code belong to the newer HS2017 target code.",
        "Do not allocate HS2012 trade values to HS2017 targets from",
        "these links alone.",
        "",
        f"Output: {OUT}",
    ]

    SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    print("\nPhase 46 completed.")
    print("Register rows:", len(register))
    print("Output:", OUT)
    print("Summary:", SUMMARY)
    print("\nSummary:")
    print("\n".join(lines))

if __name__ == "__main__":
    main()

