
from pathlib import Path
import pandas as pd

BASE = Path(r"D:\Japan_Trade_Intelligence")

DATA = BASE / "data" / "processed" / "aggregated"

files = {
    "relationships": DATA / "22_hs_concordance_relationships.csv",
    "conversions": DATA / "22_hs_concordance_conversions.csv",
    "diagnostics": DATA / "22_hs_mapping_degree_diagnostics.csv",
    "relationship_types": DATA / "22_hs_relationship_type_summary.csv",
}

print("=" * 80)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 5.6 — HS MAPPING DIAGNOSTICS AUDIT")
print("=" * 80)

for name, path in files.items():
    print(f"\nChecking {name}: {path}")
    if not path.exists():
        raise FileNotFoundError(path)
    print(f"File size: {path.stat().st_size / (1024**2):.2f} MB")

relationships = pd.read_csv(files["relationships"], dtype=str)
conversions = pd.read_csv(files["conversions"], dtype=str)
diagnostics = pd.read_csv(files["diagnostics"], dtype=str)
types = pd.read_csv(files["relationship_types"], dtype=str)

print("\n1. RELATIONSHIP TABLE")
print("Shape:", relationships.shape)
print("Columns:", relationships.columns.tolist())
print(relationships.head(10).to_string(index=False))

print("\n2. CONVERSION TABLE")
print("Shape:", conversions.shape)
print("Columns:", conversions.columns.tolist())
print(conversions.head(10).to_string(index=False))

print("\n3. MAPPING DEGREE DIAGNOSTICS")
print("Shape:", diagnostics.shape)
print("Columns:", diagnostics.columns.tolist())
print(diagnostics.head(20).to_string(index=False))

print("\n4. RELATIONSHIP TYPE SUMMARY")
print(types.to_string(index=False))

print("\n5. CODE-LEVEL MAPPING DEGREE AUDIT")

required = {
    "newer_edition",
    "newer_code",
    "older_edition",
    "older_code",
}

missing = required - set(relationships.columns)

if missing:
    raise ValueError(f"Missing relationship columns: {missing}")

forward = (
    relationships.groupby(
        ["newer_edition", "older_edition", "newer_code"]
    )["older_code"]
    .nunique()
    .reset_index(name="older_codes_per_newer_code")
)

reverse = (
    relationships.groupby(
        ["newer_edition", "older_edition", "older_code"]
    )["newer_code"]
    .nunique()
    .reset_index(name="newer_codes_per_older_code")
)

print("\nNewer codes mapping to multiple older codes:")
print(
    forward[forward["older_codes_per_newer_code"] > 1]
    .groupby(["newer_edition", "older_edition"])
    .size()
    .to_string()
)

print("\nOlder codes mapping to multiple newer codes:")
print(
    reverse[reverse["newer_codes_per_older_code"] > 1]
    .groupby(["newer_edition", "older_edition"])
    .size()
    .to_string()
)

print("\n6. CONVERSION TABLE MAPPING DEGREE")

conversion_degree = (
    conversions.groupby(
        ["newer_edition", "older_edition", "newer_code"]
    )["older_code"]
    .nunique()
    .reset_index(name="older_codes_per_newer_code")
)

print(
    conversion_degree.groupby(
        ["newer_edition", "older_edition"]
    )["older_codes_per_newer_code"]
    .agg(["count", "max", "mean"])
    .to_string()
)

print("\n" + "=" * 80)
print("PHASE 5.6 DIAGNOSTIC AUDIT COMPLETED")
print("=" * 80)
