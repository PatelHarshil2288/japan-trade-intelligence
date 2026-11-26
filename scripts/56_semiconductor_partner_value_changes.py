
from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
DATA_DIR = ROOT / "data" / "processed" / "aggregated"

INPUT = DATA_DIR / "52_hs2017_semiconductor_partner_trade.csv"

OUT_ALL = DATA_DIR / "56_semiconductor_partner_value_change.csv"
OUT_GAINERS = DATA_DIR / "56_semiconductor_partner_top_gainers.csv"
OUT_LOSERS = DATA_DIR / "56_semiconductor_partner_top_losers.csv"
OUT_SUMMARY = DATA_DIR / "56_semiconductor_partner_value_change_summary.txt"

TARGET_HS6 = ["854231", "854232", "854239"]

GROUP_COLS = ["hs6", "trade_direction"]


def main():
    print("=" * 90)
    print("PHASE 56 — PARTNER ABSOLUTE TRADE VALUE CHANGES")
    print("=" * 90)

    if not INPUT.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT}")

    # ---------------------------------------------------------
    # 1. Load and validate input
    # ---------------------------------------------------------
    df = pd.read_csv(
        INPUT,
        dtype={
            "hs6": str,
            "country": str,
        },
    )

    required_columns = {
        "year",
        "hs6",
        "trade_direction",
        "country",
        "record_count",
        "value_thousand_yen",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Input file is missing required columns: {sorted(missing_columns)}"
        )

    df["year"] = pd.to_numeric(
        df["year"], errors="raise"
    ).astype(int)

    df["value_thousand_yen"] = pd.to_numeric(
        df["value_thousand_yen"], errors="raise"
    )

    df["hs6"] = (
        df["hs6"]
        .astype(str)
        .str.strip()
        .str.zfill(6)
    )

    df["country"] = (
        df["country"]
        .astype(str)
        .str.strip()
    )

    # Keep only target codes and comparison years.
    df = df[
        df["hs6"].isin(TARGET_HS6)
        & df["year"].isin([2017, 2020])
    ].copy()

    if df.empty:
        raise ValueError(
            "No records found for target HS6 codes in 2017 and 2020."
        )

    print(f"Input rows for analysis: {len(df):,}")

    # ---------------------------------------------------------
    # 2. Aggregate partner trade values
    # ---------------------------------------------------------
    grouped = df.groupby(
        [
            "year",
            "hs6",
            "trade_direction",
            "country",
        ],
        as_index=False,
    )["value_thousand_yen"].sum()

    # ---------------------------------------------------------
    # 3. Pivot 2017 and 2020 into separate columns
    # ---------------------------------------------------------
    wide = grouped.pivot_table(
        index=[
            "hs6",
            "trade_direction",
            "country",
        ],
        columns="year",
        values="value_thousand_yen",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    # Ensure both year columns exist even if one year is absent.
    if 2017 not in wide.columns:
        wide[2017] = 0

    if 2020 not in wide.columns:
        wide[2020] = 0

    wide = wide.rename(
        columns={
            2017: "value_2017_thousand_yen",
            2020: "value_2020_thousand_yen",
        }
    )

    # ---------------------------------------------------------
    # 4. Calculate absolute value changes
    # ---------------------------------------------------------
    wide["value_change_thousand_yen"] = (
        wide["value_2020_thousand_yen"]
        - wide["value_2017_thousand_yen"]
    )

    # 1 trillion yen = 1,000,000,000 thousand yen.
    wide["value_change_trillion_yen"] = (
        wide["value_change_thousand_yen"]
        / 1_000_000_000
    )

    # Percentage change is undefined if the 2017 value is zero.
    wide["value_change_pct"] = pd.NA

    nonzero_2017 = (
        wide["value_2017_thousand_yen"] != 0
    )

    wide.loc[nonzero_2017, "value_change_pct"] = (
        (
            wide.loc[
                nonzero_2017,
                "value_2020_thousand_yen",
            ]
            /
            wide.loc[
                nonzero_2017,
                "value_2017_thousand_yen",
            ]
        )
        - 1
    ) * 100

    # ---------------------------------------------------------
    # 5. Classify partner presence
    # ---------------------------------------------------------
    wide["partner_status"] = "Present in both years"

    wide.loc[
        (
            wide["value_2017_thousand_yen"] == 0
        )
        &
        (
            wide["value_2020_thousand_yen"] > 0
        ),
        "partner_status",
    ] = "Recorded in 2020 only"

    wide.loc[
        (
            wide["value_2017_thousand_yen"] > 0
        )
        &
        (
            wide["value_2020_thousand_yen"] == 0
        ),
        "partner_status",
    ] = "Recorded in 2017 only"

    # ---------------------------------------------------------
    # 6. Calculate partner shares for both years
    # ---------------------------------------------------------
    category_totals = grouped.groupby(
        [
            "year",
            "hs6",
            "trade_direction",
        ]
    )["value_thousand_yen"].sum()

    def calculate_share(row, year, value):
        key = (
            year,
            row["hs6"],
            row["trade_direction"],
        )

        total = category_totals.get(key, 0)

        if total == 0:
            return 0.0

        return float(value / total * 100)

    wide["share_2017_pct"] = wide.apply(
        lambda row: calculate_share(
            row,
            2017,
            row["value_2017_thousand_yen"],
        ),
        axis=1,
    )

    wide["share_2020_pct"] = wide.apply(
        lambda row: calculate_share(
            row,
            2020,
            row["value_2020_thousand_yen"],
        ),
        axis=1,
    )

    wide["share_change_percentage_points"] = (
        wide["share_2020_pct"]
        - wide["share_2017_pct"]
    )

    # ---------------------------------------------------------
    # 7. Sort and save all partner changes
    # ---------------------------------------------------------
    wide = wide.sort_values(
        [
            "hs6",
            "trade_direction",
            "value_change_thousand_yen",
        ],
        ascending=[
            True,
            True,
            False,
        ],
    )

    wide.to_csv(
        OUT_ALL,
        index=False,
    )

    # ---------------------------------------------------------
    # 8. Top 10 gainers and losers within each HS6/direction
    # ---------------------------------------------------------
    gainers = (
        wide.sort_values(
            [
                "hs6",
                "trade_direction",
                "value_change_thousand_yen",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
        .groupby(
            GROUP_COLS,
            group_keys=False,
        )
        .head(10)
    )

    losers = (
        wide.sort_values(
            [
                "hs6",
                "trade_direction",
                "value_change_thousand_yen",
            ],
            ascending=[
                True,
                True,
                True,
            ],
        )
        .groupby(
            GROUP_COLS,
            group_keys=False,
        )
        .head(10)
    )

    gainers.to_csv(
        OUT_GAINERS,
        index=False,
    )

    losers.to_csv(
        OUT_LOSERS,
        index=False,
    )

    # ---------------------------------------------------------
    # 9. Create text summary
    # ---------------------------------------------------------
    lines = [
        "PHASE 56 — PARTNER ABSOLUTE VALUE CHANGE",
        "Comparison: 2017 versus 2020",
        "HS6: 854231, 854232, 854239",
        "Values: thousand yen; trillion yen also provided",
        "Partner codes are numeric and not yet country-name verified.",
        "",
    ]

    for (hs6, direction), group in wide.groupby(
        GROUP_COLS,
        sort=True,
    ):
        lines.append(
            f"HS6 {hs6} — {direction}"
        )

        group = group.sort_values(
            "value_change_thousand_yen",
            ascending=False,
        )

        lines.append("Largest value increases:")

        for _, row in group.head(5).iterrows():
            lines.append(
                f"  Partner {row['country']}: "
                f"2017={row['value_2017_thousand_yen']:,.0f}; "
                f"2020={row['value_2020_thousand_yen']:,.0f}; "
                f"change={row['value_change_trillion_yen']:+.4f}T yen; "
                f"share change="
                f"{row['share_change_percentage_points']:+.2f} pp"
            )

        lines.append("Largest value decreases:")

        for _, row in group.tail(5).sort_values(
            "value_change_thousand_yen",
            ascending=True,
        ).iterrows():
            lines.append(
                f"  Partner {row['country']}: "
                f"2017={row['value_2017_thousand_yen']:,.0f}; "
                f"2020={row['value_2020_thousand_yen']:,.0f}; "
                f"change={row['value_change_trillion_yen']:+.4f}T yen; "
                f"share change="
                f"{row['share_change_percentage_points']:+.2f} pp"
            )

        lines.append("")

    OUT_SUMMARY.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # 10. Print console results
    # ---------------------------------------------------------
    display_columns = [
        "hs6",
        "trade_direction",
        "country",
        "value_2017_thousand_yen",
        "value_2020_thousand_yen",
        "value_change_trillion_yen",
        "share_change_percentage_points",
        "partner_status",
    ]

    print("\nLargest partner value increases:")

    print(
        wide.sort_values(
            "value_change_thousand_yen",
            ascending=False,
        )
        .head(20)[display_columns]
        .round(3)
        .to_string(index=False)
    )

    print("\nLargest partner value decreases:")

    print(
        wide.sort_values(
            "value_change_thousand_yen",
            ascending=True,
        )
        .head(20)[display_columns]
        .round(3)
        .to_string(index=False)
    )

    print("\nPhase 56 completed.")
    print(f"All partner changes: {OUT_ALL}")
    print(f"Top gainers: {OUT_GAINERS}")
    print(f"Top losers: {OUT_LOSERS}")
    print(f"Summary: {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
