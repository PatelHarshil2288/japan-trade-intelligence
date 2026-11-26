
from pathlib import Path
from datetime import date
from html.parser import HTMLParser
from urllib.request import Request, urlopen
import re

import pandas as pd


ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"
SCRIPT_OUTPUT = AGG

SOURCE_URL = (
    "https://www.customs.go.jp/toukei/sankou/code/country_e.htm"
)

REFERENCE_OUT = AGG / "57_japan_customs_country_code_reference.csv"
UNMAPPED_OUT = AGG / "57_semiconductor_unmapped_partner_codes.csv"

INPUTS = {
    "full": AGG / "56_semiconductor_partner_value_change.csv",
    "gainers": AGG / "56_semiconductor_partner_top_gainers.csv",
    "losers": AGG / "56_semiconductor_partner_top_losers.csv",
}


class TableParser(HTMLParser):
    """Extract HTML table rows and cell text using Python's standard library."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = None
        self.current_cell = None
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.current_row = []

        elif tag in ("td", "th") and self.current_row is not None:
            self.current_cell = []
            self.in_cell = True

        elif tag == "br" and self.in_cell:
            self.current_cell.append(" ")

    def handle_data(self, data):
        if self.in_cell and self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            text = " ".join(self.current_cell)
            text = re.sub(r"\s+", " ", text).strip()
            self.current_row.append(text)
            self.current_cell = None
            self.in_cell = False

        elif tag == "tr" and self.current_row is not None:
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = None


def fetch_official_country_reference():
    print("Downloading Japan Customs country-code page...")

    request = Request(
        SOURCE_URL,
        headers={"User-Agent": "JapanTradeIntelligence research script"},
    )

    with urlopen(request, timeout=60) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = TableParser()
    parser.feed(html)

    records = []

    for row in parser.rows:
        cleaned = [cell.strip() for cell in row if cell.strip()]

        for i, cell in enumerate(cleaned):
            if not re.fullmatch(r"\d{3}", cell):
                continue

            if i + 1 >= len(cleaned):
                continue

            code = cell
            name = cleaned[i + 1]

            # Skip table headings and malformed rows.
            if name.lower() in {"country", "code", "country name"}:
                continue

            if not name or re.fullmatch(r"\d{3}", name):
                continue

            zone = cleaned[0] if i >= 1 else ""

            records.append({
                "country_code": code,
                "country_name": name,
                "geographical_zone": zone,
                "source_url": SOURCE_URL,
                "source_access_date": date.today().isoformat(),
            })
            break

    reference = pd.DataFrame(records)

    if reference.empty:
        raise RuntimeError(
            "Could not parse country codes from Japan Customs page. "
            "The page structure may have changed. No mapping files written."
        )

    reference["country_code"] = reference["country_code"].astype(str)

    # Remove exact duplicates and check for conflicting names.
    reference = reference.drop_duplicates(
        subset=["country_code", "country_name"]
    )

    conflicts = (
        reference.groupby("country_code")["country_name"]
        .nunique()
    )
    conflicts = conflicts[conflicts > 1]

    if not conflicts.empty:
        print("WARNING: Conflicting names for codes:")
        print(conflicts.to_string())

    reference = reference.drop_duplicates(
        subset=["country_code"],
        keep="first",
    )

    reference = reference.sort_values("country_code")

    reference.to_csv(REFERENCE_OUT, index=False, encoding="utf-8-sig")

    print(f"Reference rows: {len(reference):,}")
    print(f"Saved reference: {REFERENCE_OUT}")

    return reference


def normalize_code(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()

    # Convert numeric-looking values such as 106.0 to 106.
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]

    if re.fullmatch(r"\d+", text):
        return text.zfill(3)

    return text


def enrich_file(input_path, output_path, reference):
    if not input_path.exists():
        print(f"WARNING: Missing input file: {input_path}")
        return None

    df = pd.read_csv(input_path, dtype=str)

    if df.empty:
        print(f"WARNING: Empty input file: {input_path}")
        return None

    # Find the partner-code field without changing the original data.
    possible_columns = [
        "country",
        "country_code",
        "partner_code",
        "partner",
    ]

    code_column = next(
        (col for col in possible_columns if col in df.columns),
        None,
    )

    if code_column is None:
        raise ValueError(
            f"No partner-code column found in {input_path.name}. "
            f"Columns are: {list(df.columns)}"
        )

    df["country_code"] = df[code_column].map(normalize_code)

    enriched = df.merge(
        reference[
            [
                "country_code",
                "country_name",
                "geographical_zone",
            ]
        ],
        on="country_code",
        how="left",
        validate="many_to_one",
    )

    enriched["mapping_status"] = enriched["country_name"].notna().map(
        {True: "MAPPED", False: "UNMAPPED"}
    )

    enriched.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"\nInput: {input_path.name}")
    print(f"Rows: {len(df):,}")
    print(f"Mapped rows: {enriched['country_name'].notna().sum():,}")
    print(f"Unmapped rows: {enriched['country_name'].isna().sum():,}")
    print(f"Saved: {output_path}")

    return enriched


def main():
    reference = fetch_official_country_reference()

    all_unmapped = []

    for label, input_path in INPUTS.items():
        output_path = AGG / f"57_semiconductor_partner_{label}_enriched.csv"

        enriched = enrich_file(
            input_path=input_path,
            output_path=output_path,
            reference=reference,
        )

        if enriched is not None:
            unmapped = enriched[
                enriched["country_name"].isna()
            ].copy()

            if not unmapped.empty:
                all_unmapped.append(unmapped)

    if all_unmapped:
        combined = pd.concat(all_unmapped, ignore_index=True)

        # Preserve the distinct partner codes and the file where each appeared.
        combined.to_csv(
            UNMAPPED_OUT,
            index=False,
            encoding="utf-8-sig",
        )

        print(f"\nUnmapped partner rows saved: {UNMAPPED_OUT}")
        print(
            "Unmapped codes:",
            sorted(combined["country_code"].dropna().unique().tolist()),
        )
    else:
        print("\nAll partner codes in the Phase 56 files were mapped.")

    print("\nPhase 57 completed.")


if __name__ == "__main__":
    main()

