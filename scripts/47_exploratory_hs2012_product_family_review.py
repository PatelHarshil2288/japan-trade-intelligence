
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
AGG = ROOT / "data" / "processed" / "aggregated"

INPUT = AGG / "46_hs2012_scope_limitation_register.csv"
OUT_DETAIL = AGG / "47_hs2012_product_family_review.csv"
OUT_PROFILE = AGG / "47_hs2012_product_family_keyword_profile.csv"
OUT_SUMMARY = AGG / "47_hs2012_product_family_review_summary.txt"

# Exploratory description keywords only.
# Multiple families can be assigned to one description.
FAMILY_RULES = {
    "electrical_electronic": [
        "electrical", "electric", "electronic", "circuit",
        "semiconductor", "integrated circuit", "transistor",
        "diode", "capacitor", "resistor", "inductor",
        "transformer", "switch", "connector", "relay",
        "voltage", "power supply"
    ],
    "telecommunications": [
        "telephone", "telecommunication", "telecom",
        "transmission", "radio", "wireless", "network",
        "data processing", "communication"
    ],
    "measurement_testing_control": [
        "measuring", "measurement", "testing", "test instrument",
        "checking", "control", "controlling", "recording",
        "thermostat", "pressure", "temperature", "flow",
        "oscilloscope", "multimeter", "instrument"
    ],
    "machinery_equipment": [
        "machine", "machinery", "apparatus", "equipment",
        "mechanical", "engine", "motor", "pump",
        "compressor", "industrial"
    ],
    "transport_vehicles": [
        "vehicle", "automobile", "motor car", "aircraft",
        "ship", "vessel", "railway", "transport"
    ],
    "medical_optical_scientific": [
        "medical", "surgical", "optical", "lens",
        "microscope", "spectrometer", "scientific",
        "diagnostic"
    ],
    "weapons_ammunition": [
        "weapon", "arms", "ammunition", "cartridge",
        "firearm", "military", "projectile"
    ],
    "games_sport_miscellaneous": [
        "game", "gaming", "sport", "toy", "bowling",
        "playing card", "recreational"
    ],
    "materials_chemicals": [
        "chemical", "compound", "metal", "alloy",
        "plastic", "rubber", "ceramic", "material",
        "waste", "scrap"
    ],
}

def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    df = pd.read_csv(INPUT, dtype=str).fillna("")

    required = [
        "hs2012_code",
        "hs2012_description",
        "hs2017_target_codes",
        "has_ex_relationship",
        "source_relationship_labels",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns: {missing}. Found: {list(df.columns)}"
        )

    df["description_lower"] = (
        df["hs2012_description"].astype(str).str.lower()
    )

    family_columns = []

    for family, keywords in FAMILY_RULES.items():
        col = f"keyword_{family}"
        family_columns.append(col)

        def match_keywords(text):
            return sorted({
                keyword for keyword in keywords
                if keyword in text
            })

        matches = df["description_lower"].apply(match_keywords)
        df[col] = matches.apply(lambda x: ";".join(x))
        df[f"{col}_matched"] = matches.apply(bool)

    matched_families = []
    matched_keywords = []

    for _, row in df.iterrows():
        families = [
            family.replace("keyword_", "")
            for family in family_columns
            if bool(row[f"{family}_matched"])
        ]

        keywords = []
        for family in family_columns:
            value = row[family]
            if value:
                keywords.extend(value.split(";"))

        matched_families.append(";".join(families))
        matched_keywords.append(";".join(sorted(set(keywords))))

    df["exploratory_family_tags"] = matched_families
    df["matched_keywords"] = matched_keywords
    df["keyword_family_count"] = df["exploratory_family_tags"].apply(
        lambda x: len(x.split(";")) if x else 0
    )

    df["review_priority"] = df["keyword_family_count"].apply(
        lambda n: (
            "High - no keyword family matched"
            if n == 0 else
            "Review - multiple keyword families"
            if n > 1 else
            "Review - single keyword family"
        )
    )

    df["classification_warning"] = (
        "Keyword tags are exploratory only; they do not identify "
        "the exact goods covered by the ex relationship."
    )

    # Keep original register fields and append review fields.
    df.drop(columns=["description_lower"], inplace=True)
    df.to_csv(OUT_DETAIL, index=False)

    # Count code hits for each family.
    profile_rows = []
    for family, keywords in FAMILY_RULES.items():
        col = f"keyword_{family}"
        matched = df[df[f"{col}_matched"]]

        profile_rows.append({
            "exploratory_family": family,
            "hs2012_code_count": len(matched),
            "keyword_list": ";".join(keywords),
            "interpretation": "Description keyword signal only",
        })

    profile = pd.DataFrame(profile_rows).sort_values(
        "hs2012_code_count", ascending=False
    )
    profile.to_csv(OUT_PROFILE, index=False)

    unmatched = int((df["keyword_family_count"] == 0).sum())
    multi = int((df["keyword_family_count"] > 1).sum())

    lines = [
        "PHASE 47 — EXPLORATORY PRODUCT-FAMILY REVIEW",
        f"Input HS2012 codes: {len(df):,}",
        f"Codes with no keyword family: {unmatched:,}",
        f"Codes matching multiple families: {multi:,}",
        "",
        "Keyword family code counts:",
    ]

    for _, row in profile.iterrows():
        lines.append(
            f"{row['exploratory_family']}: "
            f"{row['hs2012_code_count']:,}"
        )

    lines += [
        "",
        "Caution:",
        "This is a keyword-based description review, not an official",
        "product classification or an interpretation of the exact ex scope.",
        "Do not use these tags to allocate trade values.",
        "",
        f"Detailed review: {OUT_DETAIL}",
        f"Family profile: {OUT_PROFILE}",
    ]

    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    print("\nPhase 47 completed.")
    print("Input codes:", len(df))
    print("No keyword family matched:", unmatched)
    print("Multiple family matches:", multi)
    print("Detail:", OUT_DETAIL)
    print("Profile:", OUT_PROFILE)
    print("Summary:", OUT_SUMMARY)
    print("\n".join(lines))

if __name__ == "__main__":
    main()
