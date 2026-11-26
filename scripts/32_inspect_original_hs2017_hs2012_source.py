from pathlib import Path
import csv
import re
from openpyxl import load_workbook

ROOT = Path(r"D:\Japan_Trade_Intelligence")
REFERENCE_DIR = ROOT / "data" / "reference" / "hs_concordance"

WORKBOOK_NAME = "HS2017toHS2012ConversionAndCorrelationTables.xlsx"

TARGET_CODES = {"854231", "854232", "854239"}
SAMPLE_OLDER_CODES = {"842211", "842220", "843110", "844311"}

OUTPUT_DIR = ROOT / "data" / "processed" / "aggregated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "32_original_source_matching_rows.csv"

print("=" * 80)
print("PHASE 5.12 — INSPECT ORIGINAL HS2017-HS2012 WORKBOOK")
print("=" * 80)

matches = list(REFERENCE_DIR.rglob(WORKBOOK_NAME))

if len(matches) != 1:
    print(f"\nWorkbook matches found: {len(matches)}")
    for path in matches:
        print(path)

    raise FileNotFoundError(
        "Expected exactly one source workbook. "
        "Check the filename and reference folder."
    )

workbook_path = matches[0]

print("\nWorkbook:")
print(workbook_path)

wb = load_workbook(
    workbook_path,
    read_only=True,
    data_only=True
)

print("\nWorkbook sheets:")
for ws in wb.worksheets:
    print(f"- {ws.title}: {ws.max_row} rows x {ws.max_column} columns")

target_sheet_name = "Correlation HS17-HS12"

if target_sheet_name not in wb.sheetnames:
    raise ValueError(
        f"Expected sheet not found: {target_sheet_name}"
    )

ws = wb[target_sheet_name]

print(f"\nInspecting sheet: {ws.title}")

def normalize_code(value):
    if value is None:
        return ""

    text = str(value).strip()

    # Excel may expose numeric codes as 854231.0
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]

    # Keep only digits for code matching
    digits = re.sub(r"\D", "", text)

    return digits

rows_to_save = []
target_hits = 0
older_hits = 0

print("\nFIRST 12 SOURCE ROWS")
for row_num, row in enumerate(
    ws.iter_rows(min_row=1, max_row=12, values_only=True),
    start=1
):
    print(f"Row {row_num}: {row}")

print("\nROWS CONTAINING TARGET HS2017 CODES")

for row_num, row in enumerate(
    ws.iter_rows(values_only=True),
    start=1
):
    normalized = [normalize_code(value) for value in row]

    matched_targets = TARGET_CODES.intersection(normalized)
    matched_older = SAMPLE_OLDER_CODES.intersection(normalized)

    if matched_targets:
        target_hits += 1

        if target_hits <= 40:
            print(f"\nSource row {row_num}")
            print("Target codes:", sorted(matched_targets))
            print(row)

        rows_to_save.append({
            "source_row": row_num,
            "match_type": "target_hs2017",
            "matched_codes": ";".join(sorted(matched_targets)),
            "source_values": repr(row)
        })

    if matched_older:
        older_hits += 1

        rows_to_save.append({
            "source_row": row_num,
            "match_type": "sample_hs2012",
            "matched_codes": ";".join(sorted(matched_older)),
            "source_values": repr(row)
        })

print("\nMATCH COUNTS")
print("Rows containing target HS2017 codes:", target_hits)
print("Rows containing sample HS2012 codes:", older_hits)

with open(
    OUTPUT_CSV,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "source_row",
            "match_type",
            "matched_codes",
            "source_values"
        ]
    )

    writer.writeheader()
    writer.writerows(rows_to_save)

print("\nSaved source rows:")
print(OUTPUT_CSV)

wb.close()

print("\n" + "=" * 80)
print("PHASE 5.12 COMPLETED")
print("=" * 80)