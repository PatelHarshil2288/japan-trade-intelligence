
from pathlib import Path
import pandas as pd

DATA = Path(
    r"D:\Japan_Trade_Intelligence\data\processed\aggregated"
)

classification_file = DATA / "22_hs_classification_codes.csv"
mismatch_file = DATA / "25_relationship_label_mismatches.csv"

print("=" * 80)
print("PHASE 5.8 — SCHEMA AND MISMATCH INSPECTION")
print("=" * 80)

# Inspect classification schema
classification = pd.read_csv(
    classification_file,
    dtype=str,
    nrows=10
)

print("\nCLASSIFICATION CSV COLUMNS:")
for column in classification.columns:
    print(f"  - {column}")

print("\nCLASSIFICATION SAMPLE:")
print(classification.head(10).to_string(index=False))

# Inspect relationship mismatch file
if mismatch_file.exists():
    mismatches = pd.read_csv(mismatch_file, dtype=str)

    print("\nMISMATCH FILE COLUMNS:")
    for column in mismatches.columns:
        print(f"  - {column}")

    print("\nMISMATCH ROW COUNT:", len(mismatches))

    print("\nMISMATCH SAMPLE:")
    print(mismatches.head(20).to_string(index=False))

    print("\nMISMATCH COUNTS BY TRANSITION:")
    print(
        mismatches.groupby(
            ["newer_edition", "older_edition"]
        ).size().to_string()
    )
else:
    print("\nMismatch file not found.")
    print("The earlier script may not have saved it.")

print("\n" + "=" * 80)
print("SCHEMA INSPECTION COMPLETED")
print("=" * 80)
