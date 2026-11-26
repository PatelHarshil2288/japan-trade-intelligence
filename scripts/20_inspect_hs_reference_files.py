
from pathlib import Path
import pandas as pd

BASE = Path(
    r"D:\Japan_Trade_Intelligence\data\reference\hs_concordance"
)

print("=" * 75)
print("HS REFERENCE FILE INSPECTION")
print("=" * 75)

# ------------------------------------------------------------
# Inspect Excel workbooks
# ------------------------------------------------------------

excel_files = sorted(
    list(BASE.glob("*.xls")) +
    list(BASE.glob("*.xlsx"))
)

for file in excel_files:
    print("\n" + "=" * 75)
    print("FILE:", file.name)
    print("=" * 75)

    try:
        workbook = pd.ExcelFile(file)

        print("SHEETS:", workbook.sheet_names)

        for sheet in workbook.sheet_names:
            print("\nSHEET:", sheet)

            df = pd.read_excel(
                file,
                sheet_name=sheet,
                header=None,
                nrows=8
            )

            print("PREVIEW:")
            print(df.to_string(index=False, header=False))

    except Exception as error:
        print("ERROR:", repr(error))

# ------------------------------------------------------------
# Inspect CSV classification files
# ------------------------------------------------------------

csv_files = sorted(BASE.glob("*.csv"))

for file in csv_files:
    print("\n" + "=" * 75)
    print("CSV FILE:", file.name)
    print("=" * 75)

    try:
        df = pd.read_csv(
            file,
            dtype=str,
            nrows=8,
            encoding="utf-8-sig"
        )

        print("COLUMNS:", list(df.columns))
        print("PREVIEW:")
        print(df.to_string(index=False))

    except Exception as error:
        print("ERROR:", repr(error))

print("\n" + "=" * 75)
print("REFERENCE FILE INSPECTION COMPLETED")
print("=" * 75)
