
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
DATA_DIR = ROOT / "data" / "processed" / "aggregated"

CONC_FILE = DATA_DIR / "54_semiconductor_partner_concentration.csv"
PARTNER_FILE = DATA_DIR / "52_hs2017_semiconductor_partner_trade.csv"

OUT_TREND = DATA_DIR / "55_semiconductor_concentration_trend.csv"
OUT_PARTNER_CHANGE = DATA_DIR / "55_semiconductor_partner_share_change.csv"
OUT_SUMMARY = DATA_DIR / "55_semiconductor_concentration_trend_summary.txt"

def main():
    print("=" * 90)
    print("PHASE 55 — PARTNER CONCENTRATION TRENDS, 2017 TO 2020")
    print("=" * 90)

    conc = pd.read_csv(CONC_FILE, dtype={"hs6": str, "top1_partner_code": str})
    partners = pd.read_csv(
        PARTNER_FILE,
        dtype={"hs6": str, "country": str},
    )

    conc["year"] = pd.to_numeric(conc["year"], errors="raise").astype(int)
    partners["year"] = pd.to_numeric(partners["year"], errors="raise").astype(int)
    partners["value_thousand_yen"] = pd.to_numeric(
        partners["value_thousand_yen"], errors="raise"
    )

    conc = conc[conc["year"].isin([2017, 2020])].copy()
    partners = partners[partners["year"].isin([2017, 2020])].copy()

    # Concentration change between 2017 and 2020.
    metrics = [
        "partner_count",
        "top1_share_pct",
        "top5_share_pct",
        "hhi_0_10000",
    ]

    trend = conc.pivot_table(
        index=["hs6", "trade_direction"],
        columns="year",
        values=metrics,
        aggfunc="first",
    )

    rows = []
    for (hs6, direction), row in trend.iterrows():
        result = {
            "hs6": hs6,
            "trade_direction": direction,
        }

        for metric in metrics:
            value_2017 = row.get((metric, 2017))
            value_2020 = row.get((metric, 2020))

            result[f"{metric}_2017"] = value_2017
            result[f"{metric}_2020"] = value_2020

            if pd.notna(value_2017) and pd.notna(value_2020):
                result[f"{metric}_change"] = value_2020 - value_2017
            else:
                result[f"{metric}_change"] = None

        rows.append(result)

    trend_out = pd.DataFrame(rows).sort_values(
        ["hs6", "trade_direction"]
    )
    trend_out.to_csv(OUT_TREND, index=False)

    # Partner share by year, HS6, and trade direction.
    partner_totals = partners.groupby(
        ["year", "hs6", "trade_direction", "country"],
        as_index=False,
    )["value_thousand_yen"].sum()

    totals = partner_totals.groupby(
        ["year", "hs6", "trade_direction"],
    )["value_thousand_yen"].transform("sum")

    partner_totals["partner_share_pct"] = (
        partner_totals["value_thousand_yen"] / totals * 100
    )

    share_wide = partner_totals.pivot_table(
        index=["hs6", "trade_direction", "country"],
        columns="year",
        values="partner_share_pct",
        aggfunc="sum",
    ).reset_index()

    if 2017 not in share_wide.columns:
        share_wide[2017] = 0
    if 2020 not in share_wide.columns:
        share_wide[2020] = 0

    share_wide[2017] = share_wide[2017].fillna(0)
    share_wide[2020] = share_wide[2020].fillna(0)

    share_wide = share_wide.rename(
        columns={
            2017: "share_pct_2017",
            2020: "share_pct_2020",
        }
    )

    share_wide["share_change_percentage_points"] = (
        share_wide["share_pct_2020"] - share_wide["share_pct_2017"]
    )

    share_wide.to_csv(OUT_PARTNER_CHANGE, index=False)

    # Text summary.
    lines = [
        "PHASE 55 — PARTNER CONCENTRATION CHANGE",
        "Comparison: 2017 versus 2020",
        "HS6: 854231, 854232, 854239",
        "",
        "Concentration metric changes:",
    ]

    for _, row in trend_out.iterrows():
        lines.append(
            f"HS6 {row['hs6']} {row['trade_direction']}: "
            f"top1 {row['top1_share_pct_2017']:.2f}% -> "
            f"{row['top1_share_pct_2020']:.2f}% "
            f"(change {row['top1_share_pct_change']:+.2f} pp); "
            f"top5 {row['top5_share_pct_2017']:.2f}% -> "
            f"{row['top5_share_pct_2020']:.2f}% "
            f"(change {row['top5_share_pct_change']:+.2f} pp); "
            f"HHI {row['hhi_0_10000_2017']:.1f} -> "
            f"{row['hhi_0_10000_2020']:.1f}"
        )

    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    print("\nConcentration change:")
    print(trend_out.round(2).to_string(index=False))

    print("\nLargest partner-share increases:")
    print(
        share_wide.sort_values(
            "share_change_percentage_points", ascending=False
        ).head(15).round(2).to_string(index=False)
    )

    print("\nLargest partner-share decreases:")
    print(
        share_wide.sort_values(
            "share_change_percentage_points", ascending=True
        ).head(15).round(2).to_string(index=False)
    )

    print("\nPhase 55 completed.")
    print(f"Trend: {OUT_TREND}")
    print(f"Partner share changes: {OUT_PARTNER_CHANGE}")
    print(f"Summary: {OUT_SUMMARY}")

if __name__ == "__main__":
    main()
