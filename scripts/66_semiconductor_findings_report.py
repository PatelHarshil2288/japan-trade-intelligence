from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence\data\processed\aggregated")
REPORTS = Path(r"D:\Japan_Trade_Intelligence\reports")

p59 = pd.read_csv(ROOT / "59_semiconductor_country_aggregate_shifts.csv")
p61 = pd.read_csv(ROOT / "61_semiconductor_hs6_contribution_matrix.csv")
p63 = pd.read_csv(ROOT / "63_semiconductor_country_net_change_ranking.csv")
directional = pd.read_csv(REPORTS / "65_semiconductor_directional_totals.csv")
qa = pd.read_csv(REPORTS / "65_semiconductor_qa_checks.csv")

REPORTS.mkdir(parents=True, exist_ok=True)

# Country-level changes by trade direction
country_changes = p59[
    [
        "country_code",
        "country_name",
        "trade_direction",
        "value_2017_thousand_yen",
        "value_2020_thousand_yen",
        "value_change_trillion_yen",
        "value_change_pct",
        "share_2017_pct",
        "share_2020_pct",
        "share_change_percentage_points",
        "rank_2017",
        "rank_2020",
        "rank_change",
    ]
].copy()

country_changes = country_changes.sort_values(
    ["trade_direction", "value_change_trillion_yen"],
    ascending=[True, False],
)

country_csv = REPORTS / "66_semiconductor_country_changes.csv"
country_changes.to_csv(country_csv, index=False, encoding="utf-8-sig")

# Aggregate the three HS6 code contributions by trade direction
hs6_rows = []
for direction in ["Export", "Import"]:
    subset = p61[p61["trade_direction"] == direction]
    for code in ["854231", "854232", "854239"]:
        col = f"change_{code}_trillion_yen"
        hs6_rows.append({
            "trade_direction": direction,
            "hs6_code": code,
            "change_trillion_yen": float(subset[col].sum()),
        })

hs6_totals = pd.DataFrame(hs6_rows)
hs6_csv = REPORTS / "66_semiconductor_hs6_directional_contributions.csv"
hs6_totals.to_csv(hs6_csv, index=False, encoding="utf-8-sig")

def trillion(value):
    return f"{value:+.6f} trillion yen"

def country_section(direction):
    subset = country_changes[country_changes["trade_direction"] == direction]
    positive = subset[subset["value_change_trillion_yen"] > 0].head(10)
    negative = subset[subset["value_change_trillion_yen"] < 0].sort_values(
        "value_change_trillion_yen"
    ).head(10)

    lines = [f"### {direction} — largest increases"]
    if positive.empty:
        lines.append("No positive country changes in this group.")
    else:
        for _, row in positive.iterrows():
            lines.append(
                f"- {row['country_name']}: "
                f"{trillion(row['value_change_trillion_yen'])}"
            )

    lines += ["", f"### {direction} — largest decreases"]
    if negative.empty:
        lines.append("No negative country changes in this group.")
    else:
        for _, row in negative.iterrows():
            lines.append(
                f"- {row['country_name']}: "
                f"{trillion(row['value_change_trillion_yen'])}"
            )
    return "\n".join(lines)

def hs6_section(direction):
    subset = hs6_totals[hs6_totals["trade_direction"] == direction]
    subset = subset.sort_values("change_trillion_yen", ascending=False)
    lines = [f"### {direction} HS6 contributions"]
    for _, row in subset.iterrows():
        lines.append(
            f"- HS6 {row['hs6_code']}: "
            f"{trillion(row['change_trillion_yen'])}"
        )
    return "\n".join(lines)

export_change = float(
    directional.loc[
        directional["trade_direction"] == "Export",
        "phase59_change_trillion_yen"
    ].iloc[0]
)
import_change = float(
    directional.loc[
        directional["trade_direction"] == "Import",
        "phase59_change_trillion_yen"
    ].iloc[0]
)
balance_change = export_change - import_change

qa_pass = (qa["status"].astype(str).str.upper() == "PASS").all()

report = f"""# Japan Semiconductor Trade: 2017–2020 Findings

## Executive summary

This report examines Japan's trade changes between 2017 and 2020 for
three selected semiconductor HS6 categories: **854231, 854232, and 854239**.

- Selected-category exports changed by **{trillion(export_change)}**.
- Selected-category imports changed by **{trillion(import_change)}**.
- The implied change in the selected-category trade balance was
  **{trillion(balance_change)}**.

These results describe changes between two comparison years. They do not
establish why trade changed and should not be interpreted as covering all
semiconductor products.

## Country-level changes

Country changes are reported separately for exports and imports.
The rankings below are based on absolute net change in the selected
categories, not on total trade with each country.

{country_section("Export")}

{country_section("Import")}

## HS6 product contributions

The following values aggregate each selected HS6 code's contribution
across country rows within the relevant trade direction.

{hs6_section("Export")}

{hs6_section("Import")}

## Data validation

Phase 65 cross-phase QA status: **{"PASS" if qa_pass else "FAIL"}**

The QA checks compare Phase 59, 61, 62, and 63 outputs, validate the
three-code HS6 coverage, and verify heatmap row counts.

## Scope and interpretation

- Period: 2017 versus 2020.
- Product scope: HS6 854231, 854232, and 854239 only.
- Values are expressed in trillion yen for changes.
- Country changes are descriptive; they do not imply causation.
- This is not a complete analysis of all semiconductor trade.
- The 2017–2020 comparison does not establish a continuous annual trend.

## Reproducibility and artifacts

- Phase 59 country aggregate shifts
- Phase 61 HS6 contribution matrix
- Phase 62 country/HS6 driver ranking
- Phase 63 country net-change ranking and heatmap data
- Phase 65 cross-phase QA reports
- Interactive dashboard: `semiconductor_trade_dashboard_2017_2020.html`

## Conclusion

Within the three selected HS6 categories, exports increased modestly,
imports decreased more substantially, and the selected-category trade
balance improved between 2017 and 2020. Country and product-level
contributions show where these net changes were concentrated; they
should be interpreted within the stated product and time scope.
"""

report_path = REPORTS / "66_semiconductor_findings_report.md"
report_path.write_text(report, encoding="utf-8")

print("PHASE 66 - FINDINGS REPORT")
print(f"QA status: {'PASS' if qa_pass else 'FAIL'}")
print(f"Export change: {trillion(export_change)}")
print(f"Import change: {trillion(import_change)}")
print(f"Trade balance change: {trillion(balance_change)}")
print(f"Report: {report_path}")
print(f"Country changes CSV: {country_csv}")
print(f"HS6 contributions CSV: {hs6_csv}")
