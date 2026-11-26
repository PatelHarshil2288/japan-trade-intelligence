from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(r"D:\Japan_Trade_Intelligence")
DATA = ROOT / "data" / "processed" / "aggregated"

HEATMAP_FILE = DATA / "63_semiconductor_hs6_heatmap_data.csv"
RANKING_FILE = DATA / "63_semiconductor_country_net_change_ranking.csv"

OUTPUT = ROOT / "reports" / "semiconductor_trade_dashboard_2017_2020.html"

HS6_LABELS = {
    "854231": "854231 - Processors/controllers",
    "854232": "854232 - Memories",
    "854239": "854239 - Other electronic integrated circuits",
}

def load_data():
    heatmap = pd.read_csv(HEATMAP_FILE, dtype={"hs6": str})
    ranking = pd.read_csv(RANKING_FILE)

    required_heatmap = {
        "country_name",
        "trade_direction",
        "hs6",
        "change_trillion_yen",
        "total_change_trillion_yen",
    }

    required_ranking = {
        "country_name",
        "trade_direction",
        "total_change_trillion_yen",
    }

    missing_heatmap = required_heatmap - set(heatmap.columns)
    missing_ranking = required_ranking - set(ranking.columns)

    if missing_heatmap:
        raise ValueError(f"Missing heatmap columns: {sorted(missing_heatmap)}")

    if missing_ranking:
        raise ValueError(f"Missing ranking columns: {sorted(missing_ranking)}")

    return heatmap, ranking

def add_heatmap(fig, heatmap, direction, row, col):
    subset = heatmap[heatmap["trade_direction"] == direction].copy()

    country_totals = (
        subset.groupby("country_name")["total_change_trillion_yen"]
        .first()
    )

    selected_countries = (
        country_totals.abs()
        .sort_values(ascending=False)
        .head(25)
        .index
        .tolist()
    )

    subset = subset[subset["country_name"].isin(selected_countries)]

    pivot = subset.pivot(
        index="country_name",
        columns="hs6",
        values="change_trillion_yen",
    )

    hs6_order = ["854231", "854232", "854239"]
    pivot = pivot.reindex(columns=hs6_order)

    pivot = pivot.loc[
        pivot.abs().max(axis=1).sort_values(ascending=True).index
    ]

    fig.add_trace(
        go.Heatmap(
            z=pivot.values,
            x=[HS6_LABELS[code] for code in pivot.columns],
            y=pivot.index.tolist(),
            colorscale="RdBu",
            zmid=0,
            colorbar=dict(title="Change<br>(trillion yen)"),
            hovertemplate=(
                "Country: %{y}<br>"
                "HS6: %{x}<br>"
                "Change: %{z:.4f} trillion yen"
                "<extra></extra>"
            ),
        ),
        row=row,
        col=col,
    )

def add_net_change_bars(fig, ranking, direction, row, col):
    subset = ranking[ranking["trade_direction"] == direction].copy()

    positive = subset[subset["total_change_trillion_yen"] > 0].nlargest(
        10, "total_change_trillion_yen"
    )

    negative = subset[subset["total_change_trillion_yen"] < 0].nsmallest(
        10, "total_change_trillion_yen"
    )

    selected = pd.concat([positive, negative], ignore_index=True)
    selected = selected.sort_values("total_change_trillion_yen")

    fig.add_trace(
        go.Bar(
            x=selected["total_change_trillion_yen"],
            y=selected["country_name"],
            orientation="h",
            hovertemplate=(
                "Country: %{y}<br>"
                "Net change: %{x:.4f} trillion yen"
                "<extra></extra>"
            ),
            name=direction,
        ),
        row=row,
        col=col,
    )

def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    heatmap, ranking = load_data()

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=[
            "Exports - HS6 change by country",
            "Imports - HS6 change by country",
            "Exports - largest country net changes",
            "Imports - largest country net changes",
        ],
        specs=[
            [{"type": "heatmap"}, {"type": "heatmap"}],
            [{"type": "bar"}, {"type": "bar"}],
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.12,
    )

    add_heatmap(fig, heatmap, "Export", 1, 1)
    add_heatmap(fig, heatmap, "Import", 1, 2)

    add_net_change_bars(fig, ranking, "Export", 2, 1)
    add_net_change_bars(fig, ranking, "Import", 2, 2)

    fig.update_layout(
        title={
            "text": (
                "Japan Semiconductor Trade Intelligence"
                "<br><sup>2017 to 2020 | HS6 854231, 854232, 854239"
                " | Value changes in trillion yen</sup>"
            ),
            "x": 0.5,
        },
        height=1500,
        width=1800,
        template="plotly_white",
        showlegend=False,
        margin=dict(l=140, r=80, t=120, b=80),
    )

    fig.update_xaxes(title_text="HS6 category", row=1, col=1)
    fig.update_xaxes(title_text="HS6 category", row=1, col=2)
    fig.update_xaxes(title_text="Net change (trillion yen)", row=2, col=1)
    fig.update_xaxes(title_text="Net change (trillion yen)", row=2, col=2)

    fig.update_yaxes(title_text="Country", row=1, col=1)
    fig.update_yaxes(title_text="Country", row=1, col=2)
    fig.update_yaxes(title_text="Country", row=2, col=1)
    fig.update_yaxes(title_text="Country", row=2, col=2)

    fig.write_html(
        OUTPUT,
        include_plotlyjs=True,
        full_html=True,
    )

    print("PHASE 64 COMPLETE")
    print(f"Dashboard: {OUTPUT}")
    print(f"Heatmap input rows: {len(heatmap):,}")
    print(f"Ranking input rows: {len(ranking):,}")
    print(f"Dashboard size: {OUTPUT.stat().st_size:,} bytes")

if __name__ == "__main__":
    main()
