
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
DATA_DIR = ROOT / "data" / "processed" / "aggregated"

FILES = [
    "52_hs2017_semiconductor_annual_trade.csv",
    "52_hs2017_semiconductor_monthly_trade.csv",
    "52_hs2017_semiconductor_partner_trade.csv",
    "52_hs2017_semiconductor_hs9_detail.csv",
]

print("=" * 90)
print("PHASE 53 — PHASE 52 OUTPUT SCHEMA INSPECTION")
print("=" * 90)

for filename in FILES:
    path = DATA_DIR / filename
    print(f"\n\nFILE: {filename}")
    print("-" * 90)

    if not path.exists():
        print("ERROR: File not found")
        continue

    try:
        df = pd.read_csv(path, nrows=5, dtype=str)

        print(f"Columns ({len(df.columns)}):")
        for column in df.columns:
            print(f"  - {column}")

        print("\nFirst 5 rows:")
        print(df.to_string(index=False))

        print(f"\nFile size: {path.stat().st_size:,} bytes")

    except Exception as exc:
        print(f"ERROR reading file: {exc}")

print("\n\nPhase 53 inspection completed.")
