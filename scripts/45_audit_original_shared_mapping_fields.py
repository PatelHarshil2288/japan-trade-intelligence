
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

SOURCE = AGG / "36_hs2017_ic_original_source_rows.csv"
SHARED = AGG / "40_shared_hs2017_ic_scope_details.csv"

OUT_FIELDS = AGG / "45_original_source_field_audit.csv"
OUT_ROWS = AGG / "45_original_shared_mapping_source_rows.csv"
OUT_SUMMARY = AGG / "45_original_shared_mapping_audit_summary.txt"

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing source file: {SOURCE}")
    if not SHARED.exists():
        raise FileNotFoundError(f"Missing shared mapping file: {SHARED}")

    source = pd.read_csv(SOURCE, dtype=str).fillna("")
    shared = pd.read_csv(SHARED, dtype=str).fillna("")

    print("Original source file:", SOURCE.name)
    print("Original source rows:", len(source))
    print("Original source columns:")
    for col in source.columns:
        print(f"  - {col}")

    # Document field availability before making any scope interpretation.
    field_audit = pd.DataFrame({
        "column": source.columns,
        "nonblank_values": [
            int(source[col].astype(str).str.strip().ne("").sum())
            for col in source.columns
        ],
        "distinct_nonblank_values": [
            int(source[col].astype(str).str.strip().replace("", pd.NA).nunique())
            for col in source.columns
        ],
    })
    field_audit.to_csv(OUT_FIELDS, index=False)

    # Identify shared older codes using the Phase 40 output.
    older_col = next(
        (c for c in shared.columns
         if c.lower() in {"older_code", "hs2012_code", "hs2012", "hs12_code"}),
        None
    )
    if older_col is None:
        raise ValueError(
            "Could not identify older HS2012 code column in Phase 40 file. "
            f"Columns found: {list(shared.columns)}"
        )

    shared_codes = set(
        shared[older_col].astype(str).str.strip().replace("", pd.NA).dropna()
    )

    # Find the older-code column in the original Phase 36 source.
    source_older_col = next(
        (c for c in source.columns
         if c.lower() in {"older_code", "hs2012_code", "hs2012", "hs12_code"}),
        None
    )
    if source_older_col is None:
        raise ValueError(
            "Could not identify older HS2012 code column in Phase 36 source. "
            f"Columns found: {list(source.columns)}"
        )

    selected = source[
        source[source_older_col].astype(str).str.strip().isin(shared_codes)
    ].copy()

    selected.to_csv(OUT_ROWS, index=False)

    # Build concise audit summary.
    lines = [
        "PHASE 45 — ORIGINAL SOURCE ROW AUDIT",
        f"Original source rows: {len(source):,}",
        f"Original source columns: {len(source.columns)}",
        f"Shared HS2012 codes: {len(shared_codes):,}",
        f"Selected original source rows: {len(selected):,}",
        "",
        "Source fields and completeness:",
    ]

    for _, row in field_audit.iterrows():
        lines.append(
            f"{row['column']}: nonblank={row['nonblank_values']:,}; "
            f"distinct={row['distinct_nonblank_values']:,}"
        )

    lines += [
        "",
        "Selected-row distinct values for likely scope/relationship fields:",
    ]

    likely_terms = (
        "ex", "relation", "scope", "note", "remark", "comment",
        "description", "text", "type", "source", "chapter"
    )

    for col in selected.columns:
        if any(term in col.lower() for term in likely_terms):
            vals = (
                selected[col].astype(str).str.strip()
                .replace("", pd.NA).dropna().unique()
            )
            lines.append(f"{col}: {len(vals):,} distinct nonblank values")
            for value in list(vals[:20]):
                lines.append(f"    {value}")

    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    print("\nSelected source rows:", len(selected))
    print("Saved field audit:", OUT_FIELDS)
    print("Saved selected source rows:", OUT_ROWS)
    print("Saved summary:", OUT_SUMMARY)
    print("\nNext: share the printed columns and summary output.")

if __name__ == "__main__":
    main()
