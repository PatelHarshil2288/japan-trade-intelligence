from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
INPUT = ROOT / "data" / "processed" / "aggregated" / "62_semiconductor_country_hs6_driver_ranking.csv"
OUTPUT = ROOT / "data" / "processed" / "aggregated"

HS6_COLUMNS = {
    "854231": "change_854231_trillion_yen",
    "854232": "change_854232_trillion_yen",
    "854239": "change_854239_trillion_yen",
}

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("PHASE 63 - SEMICONDUCTOR VISUALIZATION DATASETS")
    print(f"Input: {INPUT}")

    df = pd.read_csv(INPUT)

    required = [
        "country_code",
        "country_name",
        "trade_direction",
        "total_change_trillion_yen",
        *HS6_COLUMNS.values(),
    ]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if df.duplicated(["country_code", "trade_direction"]).any():
        raise ValueError("Duplicate country-direction records detected.")

    # ---------------------------------------------------------
    # 1. Country x HS6 long-format dataset for heatmaps
    # ---------------------------------------------------------
    id_columns = [
        "country_code",
        "country_name",
        "trade_direction",
        "total_change_trillion_yen",
    ]

    heatmap = df[id_columns + list(HS6_COLUMNS.values())].melt(
        id_vars=id_columns,
        value_vars=list(HS6_COLUMNS.values()),
        var_name="source_hs6_column",
        value_name="change_trillion_yen",
    )

    column_to_hs6 = {
        column: hs6 for hs6, column in HS6_COLUMNS.items()
    }

    heatmap["hs6"] = heatmap["source_hs6_column"].map(column_to_hs6)
    heatmap["change_direction"] = heatmap["change_trillion_yen"].apply(
        lambda x: "Increase" if x > 0 else ("Decrease" if x < 0 else "No change")
    )

    heatmap = heatmap.drop(columns=["source_hs6_column"])
    heatmap = heatmap[
        [
            "country_code",
            "country_name",
            "trade_direction",
            "hs6",
            "change_trillion_yen",
            "total_change_trillion_yen",
            "change_direction",
        ]
    ].sort_values(
        ["trade_direction", "country_name", "hs6"]
    )

    heatmap_path = OUTPUT / "63_semiconductor_hs6_heatmap_data.csv"
    heatmap.to_csv(heatmap_path, index=False, encoding="utf-8-sig")

    # ---------------------------------------------------------
    # 2. Country net-change ranking
    # ---------------------------------------------------------
    country_rank = df[
        [
            "country_code",
            "country_name",
            "trade_direction",
            "total_change_trillion_yen",
        ]
    ].copy()

    country_rank["net_change_direction"] = country_rank[
        "total_change_trillion_yen"
    ].apply(
        lambda x: "Increase" if x > 0 else ("Decrease" if x < 0 else "No change")
    )

    country_rank = country_rank.sort_values(
        ["trade_direction", "total_change_trillion_yen"],
        ascending=[True, False],
    )

    country_rank["rank_within_direction"] = (
        country_rank.groupby("trade_direction")[
            "total_change_trillion_yen"
        ].rank(method="first", ascending=False).astype(int)
    )

    country_rank_path = OUTPUT / "63_semiconductor_country_net_change_ranking.csv"
    country_rank.to_csv(
        country_rank_path, index=False, encoding="utf-8-sig"
    )

    # Top 20 increases and decreases per trade direction
    top_changes = []

    for direction in sorted(country_rank["trade_direction"].unique()):
        subset = country_rank[
            country_rank["trade_direction"] == direction
        ]

        increases = subset[subset["total_change_trillion_yen"] > 0].nlargest(
            20, "total_change_trillion_yen"
        )

        decreases = subset[subset["total_change_trillion_yen"] < 0].nsmallest(
            20, "total_change_trillion_yen"
        )

        top_changes.extend([increases, decreases])

    top_changes_df = pd.concat(top_changes, ignore_index=True)

    top_changes_path = OUTPUT / "63_semiconductor_top_country_net_changes.csv"
    top_changes_df.to_csv(
        top_changes_path, index=False, encoding="utf-8-sig"
    )

    # ---------------------------------------------------------
    # 3. Country x HS6 driver ranking
    # ---------------------------------------------------------
    driver_data = heatmap[
        [
            "country_code",
            "country_name",
            "trade_direction",
            "hs6",
            "change_trillion_yen",
        ]
    ].copy()

    driver_data["absolute_change_trillion_yen"] = (
        driver_data["change_trillion_yen"].abs()
    )

    driver_data["change_direction"] = driver_data[
        "change_trillion_yen"
    ].apply(
        lambda x: "Increase" if x > 0 else ("Decrease" if x < 0 else "No change")
    )

    driver_data = driver_data.sort_values(
        "absolute_change_trillion_yen", ascending=False
    )

    driver_path = OUTPUT / "63_semiconductor_country_hs6_driver_magnitude.csv"
    driver_data.to_csv(driver_path, index=False, encoding="utf-8-sig")

    # ---------------------------------------------------------
    # 4. Validation
    # ---------------------------------------------------------
    summed_hs6 = (
        df[list(HS6_COLUMNS.values())].sum(axis=1)
    )

    difference = (
        summed_hs6 - df["total_change_trillion_yen"]
    ).abs()

    max_difference = float(difference.max())

    if max_difference > 1e-9:
        raise ValueError(
            f"HS6 reconciliation failed. Max difference: {max_difference}"
        )

    summary_path = OUTPUT / "63_semiconductor_visualization_summary.txt"

    summary_lines = [
        "PHASE 63 - SEMICONDUCTOR VISUALIZATION DATASETS",
        "",
        f"Input rows: {len(df):,}",
        f"Heatmap rows: {len(heatmap):,}",
        f"Country-direction rows: {len(country_rank):,}",
        f"Country-HS6 driver rows: {len(driver_data):,}",
        f"Top country changes rows: {len(top_changes_df):,}",
        f"Unique countries: {df['country_code'].nunique():,}",
        f"Trade directions: {', '.join(sorted(df['trade_direction'].unique()))}",
        f"HS6 codes: {', '.join(HS6_COLUMNS.keys())}",
        f"Maximum HS6 reconciliation difference: {max_difference:.12f} trillion yen",
        "",
        "Validation: PASSED",
        "Scope: HS6 854231, 854232, 854239; comparison 2017 to 2020.",
        "Interpretation: descriptive value changes, not causal estimates.",
    ]

    summary_path.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print("\nPHASE 63 COMPLETE")
    print(f"Heatmap data: {heatmap_path}")
    print(f"Country ranking: {country_rank_path}")
    print(f"Top country changes: {top_changes_path}")
    print(f"Country-HS6 drivers: {driver_path}")
    print(f"Summary: {summary_path}")
    print(f"Heatmap rows: {len(heatmap):,}")
    print(f"Maximum reconciliation difference: {max_difference:.12f} trillion yen")
    print("Validation: PASSED")

if __name__ == "__main__":
    main()
