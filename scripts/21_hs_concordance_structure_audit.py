
from pathlib import Path
import pandas as pd
import re

BASE = Path(
    r"D:\Japan_Trade_Intelligence\data\reference\hs_concordance"
)

TRANSITION_FILES = [
    "HS1996 to HS1992 - Correlation and conversion tables.xls",
    "HS2002 to HS1996 - Correlation and conversion tables.xls",
    "HS 2007 to HS 2002 Correlation and conversion tables.xls",
    "HS 2012 to HS 2007 Correlation and conversion tables.xls",
    "HS2017toHS2012ConversionAndCorrelationTables.xlsx",
]

print("=" * 80)
print("JAPAN TRADE INTELLIGENCE")
print("PHASE 5.5 — HS CONCORDANCE STRUCTURE AUDIT")
print("=" * 80)

# ------------------------------------------------------------
# 1. Inspect complete transition workbooks
# ------------------------------------------------------------

for filename in TRANSITION_FILES:
    file = BASE / filename

    print("\n" + "=" * 80)
    print("WORKBOOK:", filename)
    print("=" * 80)

    if not file.exists():
        print("WARNING: File not found")
        continue

    try:
        workbook = pd.ExcelFile(file)
        print("SHEETS:", workbook.sheet_names)

        for sheet in workbook.sheet_names:
            df = pd.read_excel(
                file,
                sheet_name=sheet,
                header=None,
                dtype=str
            )

            print("\n" + "-" * 70)
            print("SHEET:", sheet)
            print("ROWS:", len(df))
            print("COLUMNS:", len(df.columns))

            print("\nFIRST 10 ROWS:")
            print(df.head(10).to_string(index=False, header=False))

            print("\nLAST 5 ROWS:")
            print(df.tail(5).to_string(index=False, header=False))

            print("\nNON-EMPTY VALUES PER COLUMN:")
            print(df.count().to_string())

            # Find relationship labels, where present.
            relationship_values = set()

            for col in df.columns:
                values = (
                    df[col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                )
                relationship_values.update(
                    value for value in values
                    if value.lower() in {
                        "1:1", "1:n", "n:1", "n:n"
                    }
                )

            if relationship_values:
                print(
                    "\nRELATIONSHIP LABELS:",
                    sorted(relationship_values)
                )

            print(
                "\nEXACT DUPLICATE ROWS:",
                int(df.duplicated().sum())
            )

    except Exception as error:
        print("ERROR:", repr(error))

# ------------------------------------------------------------
# 2. Inspect UN Comtrade classification CSV files
# ------------------------------------------------------------

print("\n" + "=" * 80)
print("UN COMTRADE CLASSIFICATION FILE AUDIT")
print("=" * 80)

for file in sorted(BASE.glob("UNComtrade-cmd-H*.csv")):

    print("\n" + "-" * 70)
    print("FILE:", file.name)

    try:
        df = pd.read_csv(
            file,
            dtype=str,
            encoding="utf-8-sig"
        )

        df["id"] = df["id"].fillna("").str.strip()
        df["aggrlevel"] = df["aggrlevel"].fillna("").str.strip()
        df["isLeaf"] = df["isLeaf"].fillna("").str.strip()

        six_digit = df[
            df["id"].str.fullmatch(r"\d{6}", na=False)
        ]

        six_digit_leaves = df[
            (df["id"].str.fullmatch(r"\d{6}", na=False))
            & (df["isLeaf"] == "1")
        ]

        print("TOTAL ROWS:", len(df))
        print("UNIQUE IDS:", df["id"].nunique())
        print("DUPLICATE IDS:", int(df["id"].duplicated().sum()))
        print("SIX-DIGIT IDS:", len(six_digit))
        print("SIX-DIGIT LEAF CODES:", len(six_digit_leaves))

        print("\nAGGREGATION LEVEL COUNTS:")
        print(df["aggrlevel"].value_counts().sort_index().to_string())

        print("\nSAMPLE SIX-DIGIT LEAF CODES:")
        print(
            six_digit_leaves[
                ["id", "text", "parent", "standardUnitAbbr"]
            ].head(5).to_string(index=False)
        )

    except Exception as error:
        print("ERROR:", repr(error))

print("\n" + "=" * 80)
print("HS CONCORDANCE STRUCTURE AUDIT COMPLETED")
print("=" * 80)

