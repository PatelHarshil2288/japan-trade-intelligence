
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(r"D:\Japan_Trade_Intelligence")
DATA_DIR = ROOT / "data" / "processed" / "aggregated"

ANNUAL_FILE = DATA_DIR / "52_hs2017_semiconductor_annual_trade.csv"
PARTNER_FILE = DATA_DIR / "52_hs2017_semiconductor_partner_trade.csv"

OUT_BALANCE = DATA_DIR / "54_semiconductor_annual_balance.csv"
OUT_CONCENTRATION = DATA_DIR / "54_semiconductor_partner_concentration.csv"
OUT_TOP_PARTNERS = DATA_DIR / "54_semiconductor_top10_partners.csv"
OUT_SUMMARY = DATA_DIR / "54_semiconductor_analysis_summary.txt"

TARGET_HS6 = ["854231", "854232", "854239"]

def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return pd.read_csv(path, dtype={"hs6": str, "country": str})

def main():
    print("=" * 90)
    print("PHASE 54 — SEMICONDUCTOR ANNUAL BALANCE & PARTNER CONCENTRATION")
    print("=" * 90)

    annual = load_csv(ANNUAL_FILE)
    partners = load_csv(PARTNER_FILE)

    annual["year"] = pd.to_numeric(annual["year"], errors="raise").astype(int)
    annual["value_thousand_yen"] = pd.to_numeric(
        annual["value_thousand_yen"], errors="raise"
    )

    partners["year"] = pd.to_numeric(partners["year"], errors="raise").astype(int)
    partners["value_thousand_yen"] = pd.to_numeric(
        partners["value_thousand_yen"], errors="raise"
    )

    annual["hs6"] = annual["hs6"].astype(str).str.zfill(6)
    partners["hs6"] = partners["hs6"].astype(str).str.zfill(6)
    partners["country"] = partners["country"].astype(str)

    annual = annual[annual["hs6"].isin(TARGET_HS6)].copy()
    partners = partners[partners["hs6"].isin(TARGET_HS6)].copy()

    # ---------------------------------------------------------
    # 1. Annual exports, imports, and trade balances
    # ---------------------------------------------------------
    pivot = annual.pivot_table(
        index=["year", "hs6"],
        columns="trade_direction",
        values="value_thousand_yen",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    for col in ["Export", "Import"]:
        if col not in pivot.columns:
            pivot[col] = 0

    pivot = pivot.rename(
        columns={
            "Export": "exports_thousand_yen",
            "Import": "imports_thousand_yen",
        }
    )

    pivot["balance_thousand_yen"] = (
        pivot["exports_thousand_yen"] - pivot["imports_thousand_yen"]
    )

    pivot["exports_trillion_yen"] = (
        pivot["exports_thousand_yen"] / 1_000_000_000
    )
    pivot["imports_trillion_yen"] = (
        pivot["imports_thousand_yen"] / 1_000_000_000
    )
    pivot["balance_trillion_yen"] = (
        pivot["balance_thousand_yen"] / 1_000_000_000
    )

    pivot = pivot.sort_values(["hs6", "year"])

    for metric in ["exports_thousand_yen", "imports_thousand_yen"]:
        pivot[f"{metric}_yoy_pct"] = (
            pivot.groupby("hs6")[metric].pct_change() * 100
        )

    pivot.to_csv(OUT_BALANCE, index=False)

    # Combined total across the three target HS6 codes.
    combined = pivot.groupby("year", as_index=False).agg(
        exports_thousand_yen=("exports_thousand_yen", "sum"),
        imports_thousand_yen=("imports_thousand_yen", "sum"),
        balance_thousand_yen=("balance_thousand_yen", "sum"),
    )

    combined["hs6"] = "ALL_TARGETS"
    combined["exports_trillion_yen"] = (
        combined["exports_thousand_yen"] / 1_000_000_000
    )
    combined["imports_trillion_yen"] = (
        combined["imports_thousand_yen"] / 1_000_000_000
    )
    combined["balance_trillion_yen"] = (
        combined["balance_thousand_yen"] / 1_000_000_000
    )

    combined = combined.sort_values("year")
    combined["exports_yoy_pct"] = (
        combined["exports_thousand_yen"].pct_change() * 100
    )
    combined["imports_yoy_pct"] = (
        combined["imports_thousand_yen"].pct_change() * 100
    )

    # Append combined rows to the same annual output.
    balance_output = pd.concat([pivot, combined], ignore_index=True, sort=False)
    balance_output.to_csv(OUT_BALANCE, index=False)

    # ---------------------------------------------------------
    # 2. Partner concentration
    # ---------------------------------------------------------
    concentration_rows = []

    group_cols = ["year", "hs6", "trade_direction"]

    for keys, group in partners.groupby(group_cols, sort=True):
        year, hs6, direction = keys

        values = group.groupby("country")["value_thousand_yen"].sum()
        values = values[values > 0].sort_values(ascending=False)

        total = values.sum()
        if total <= 0:
            continue

        shares = values / total

        concentration_rows.append({
            "year": int(year),
            "hs6": hs6,
            "trade_direction": direction,
            "total_value_thousand_yen": total,
            "partner_count": int(values.size),
            "top1_partner_code": values.index[0],
            "top1_share_pct": float(shares.iloc[0] * 100),
            "top5_share_pct": float(shares.head(5).sum() * 100),
            "hhi_0_10000": float((shares.pow(2).sum()) * 10000),
        })

    concentration = pd.DataFrame(concentration_rows)
    concentration.to_csv(OUT_CONCENTRATION, index=False)

    # ---------------------------------------------------------
    # 3. Top 10 partners per year, HS6, and direction
    # ---------------------------------------------------------
    partners_sorted = partners.sort_values(
        ["year", "hs6", "trade_direction", "value_thousand_yen"],
        ascending=[True, True, True, False],
    ).copy()

    partners_sorted["partner_rank"] = (
        partners_sorted.groupby(group_cols)["value_thousand_yen"]
        .rank(method="first", ascending=False)
        .astype(int)
    )

    top10 = partners_sorted[partners_sorted["partner_rank"] <= 10].copy()
    top10.to_csv(OUT_TOP_PARTNERS, index=False)

    # ---------------------------------------------------------
    # 4. Text summary
    # ---------------------------------------------------------
    lines = [
        "PHASE 54 — SEMICONDUCTOR ANNUAL BALANCE & CONCENTRATION",
        "Period: 2017-2020",
        "HS6: 854231, 854232, 854239",
        "Values: thousand yen unless stated",
        "",
        "Combined annual trade:",
    ]

    for _, row in combined.iterrows():
        lines.append(
            f"{int(row['year'])}: "
            f"exports={row['exports_trillion_yen']:.3f} trillion yen; "
            f"imports={row['imports_trillion_yen']:.3f} trillion yen; "
            f"balance={row['balance_trillion_yen']:.3f} trillion yen"
        )

    lines.extend(["", "Annual balance by HS6:"])

    for _, row in pivot.iterrows():
        lines.append(
            f"{int(row['year'])} HS6 {row['hs6']}: "
            f"exports={row['exports_trillion_yen']:.3f}T; "
            f"imports={row['imports_trillion_yen']:.3f}T; "
            f"balance={row['balance_trillion_yen']:.3f}T"
        )

    lines.extend([
        "",
        "Concentration note:",
        "HHI is calculated as sum of squared partner market shares multiplied by 10,000.",
        "Top-1 and top-5 shares are based on partner value within each year, HS6, and direction.",
        "Country values are partner codes, not resolved country names.",
        "These results cover directly classified HS2017 records for 2017-2020 only.",
    ])

    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    print("\nCombined annual trade:")
    print(combined[
        [
            "year",
            "exports_trillion_yen",
            "imports_trillion_yen",
            "balance_trillion_yen",
            "exports_yoy_pct",
            "imports_yoy_pct",
        ]
    ].round(3).to_string(index=False))

    print("\nConcentration sample:")
    print(concentration.head(12).round(2).to_string(index=False))

    print("\nPhase 54 completed.")
    print(f"Annual balance: {OUT_BALANCE}")
    print(f"Concentration: {OUT_CONCENTRATION}")
    print(f"Top 10 partners: {OUT_TOP_PARTNERS}")
    print(f"Summary: {OUT_SUMMARY}")

if __name__ == "__main__":
    main()
