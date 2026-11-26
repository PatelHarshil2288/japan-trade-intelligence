from pathlib import Path
import pandas as pd

ROOT = Path(r"D:\Japan_Trade_Intelligence")
DATA = ROOT / "data" / "processed" / "aggregated"
REPORTS = ROOT / "reports"

FILES = {
    "phase59": DATA / "59_semiconductor_country_aggregate_shifts.csv",
    "phase61": DATA / "61_semiconductor_hs6_contribution_matrix.csv",
    "phase62": DATA / "62_semiconductor_country_hs6_driver_ranking.csv",
    "heatmap": DATA / "63_semiconductor_hs6_heatmap_data.csv",
    "ranking": DATA / "63_semiconductor_country_net_change_ranking.csv",
}

TOLERANCE = 1e-9
KEYS = ["country_code", "trade_direction"]

def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return pd.read_csv(path, dtype={"country_code": str, "hs6": str})

def assert_unique_keys(df, name, keys=KEYS):
    duplicates = df[df.duplicated(keys, keep=False)]
    if not duplicates.empty:
        raise ValueError(
            f"{name} has {len(duplicates)} rows with duplicate keys {keys}"
        )

def compare_values(left, right, left_name, right_name, left_col, right_col):
    left_part = left[KEYS + [left_col]].rename(
        columns={left_col: "left_value"}
    )
    right_part = right[KEYS + [right_col]].rename(
        columns={right_col: "right_value"}
    )

    merged = left_part.merge(
        right_part,
        on=KEYS,
        how="outer",
        indicator=True,
    )

    unmatched = merged[merged["_merge"] != "both"]
    if not unmatched.empty:
        raise ValueError(
            f"{left_name} vs {right_name}: "
            f"{len(unmatched)} unmatched country-direction keys"
        )

    merged["difference_trillion_yen"] = (
        merged["left_value"] - merged["right_value"]
    )

    merged["absolute_difference_trillion_yen"] = (
        merged["difference_trillion_yen"].abs()
    )

    max_difference = float(
        merged["absolute_difference_trillion_yen"].max()
    )

    passed = max_difference <= TOLERANCE

    return merged, max_difference, passed

def main():
    REPORTS.mkdir(parents=True, exist_ok=True)

    print("PHASE 65 - SEMICONDUCTOR DASHBOARD QA")
    print("Loading Phase 59-63 datasets...")

    p59 = load_csv(FILES["phase59"])
    p61 = load_csv(FILES["phase61"])
    p62 = load_csv(FILES["phase62"])
    heatmap = load_csv(FILES["heatmap"])
    ranking = load_csv(FILES["ranking"])

    required = {
        "phase59": ["value_change_trillion_yen"],
        "phase61": ["total_change_trillion_yen"],
        "phase62": [
            "total_change_trillion_yen",
            "change_854231_trillion_yen",
            "change_854232_trillion_yen",
            "change_854239_trillion_yen",
        ],
        "heatmap": ["hs6", "change_trillion_yen"],
        "ranking": ["total_change_trillion_yen"],
    }

    datasets = {
        "phase59": p59,
        "phase61": p61,
        "phase62": p62,
        "heatmap": heatmap,
        "ranking": ranking,
    }

    for name, columns in required.items():
        missing = [col for col in columns if col not in datasets[name].columns]
        if missing:
            raise ValueError(f"{name} missing required columns: {missing}")

    for name, df in datasets.items():
        if name != "heatmap":
            assert_unique_keys(df, name)

    checks = []

    # Check 1: Phase 59 against Phase 61
    p59_p61, diff_59_61, pass_59_61 = compare_values(
        p59,
        p61,
        "Phase 59",
        "Phase 61",
        "value_change_trillion_yen",
        "total_change_trillion_yen",
    )

    checks.append({
        "check": "Phase 59 vs Phase 61 country-direction totals",
        "max_abs_difference_trillion_yen": diff_59_61,
        "status": "PASS" if pass_59_61 else "FAIL",
    })

    # Check 2: Phase 61 against Phase 62
    p61_p62, diff_61_62, pass_61_62 = compare_values(
        p61,
        p62,
        "Phase 61",
        "Phase 62",
        "total_change_trillion_yen",
        "total_change_trillion_yen",
    )

    checks.append({
        "check": "Phase 61 vs Phase 62 country-direction totals",
        "max_abs_difference_trillion_yen": diff_61_62,
        "status": "PASS" if pass_61_62 else "FAIL",
    })

    # Check 3: Phase 62 HS6 components reconcile to net total
    hs6_sum = p62[
        [
            "change_854231_trillion_yen",
            "change_854232_trillion_yen",
            "change_854239_trillion_yen",
        ]
    ].sum(axis=1)

    hs6_diff = (
        hs6_sum - p62["total_change_trillion_yen"]
    ).abs()

    max_hs6_diff = float(hs6_diff.max())
    pass_hs6 = max_hs6_diff <= TOLERANCE

    checks.append({
        "check": "Phase 62 HS6 components vs net total",
        "max_abs_difference_trillion_yen": max_hs6_diff,
        "status": "PASS" if pass_hs6 else "FAIL",
    })

    # Check 4: Phase 63 heatmap aggregates back to Phase 62 totals
    heatmap_agg = (
        heatmap.groupby(KEYS, as_index=False)["change_trillion_yen"]
        .sum()
        .rename(
            columns={
                "change_trillion_yen": "heatmap_total_trillion_yen"
            }
        )
    )

    p62_heatmap, diff_62_heatmap, pass_62_heatmap = compare_values(
        p62,
        heatmap_agg,
        "Phase 62",
        "Phase 63 heatmap",
        "total_change_trillion_yen",
        "heatmap_total_trillion_yen",
    )

    checks.append({
        "check": "Phase 62 totals vs Phase 63 heatmap aggregates",
        "max_abs_difference_trillion_yen": diff_62_heatmap,
        "status": "PASS" if pass_62_heatmap else "FAIL",
    })

    # Check 5: Phase 63 ranking against Phase 62
    p62_ranking, diff_62_ranking, pass_62_ranking = compare_values(
        p62,
        ranking,
        "Phase 62",
        "Phase 63 ranking",
        "total_change_trillion_yen",
        "total_change_trillion_yen",
    )

    checks.append({
        "check": "Phase 62 totals vs Phase 63 country ranking",
        "max_abs_difference_trillion_yen": diff_62_ranking,
        "status": "PASS" if pass_62_ranking else "FAIL",
    })

    # Check 6: Heatmap category coverage
    expected_hs6 = {"854231", "854232", "854239"}
    observed_hs6 = set(heatmap["hs6"].dropna().astype(str))

    hs6_coverage_pass = observed_hs6 == expected_hs6

    checks.append({
        "check": "Heatmap contains exactly the three selected HS6 codes",
        "max_abs_difference_trillion_yen": 0.0,
        "status": "PASS" if hs6_coverage_pass else "FAIL",
    })

    # Check 7: Heatmap rows and country-direction coverage
    expected_heatmap_rows = len(p62) * 3
    actual_heatmap_rows = len(heatmap)

    heatmap_rows_pass = actual_heatmap_rows == expected_heatmap_rows

    checks.append({
        "check": "Heatmap row count equals country-direction rows x 3 HS6",
        "max_abs_difference_trillion_yen": 0.0,
        "status": "PASS" if heatmap_rows_pass else "FAIL",
    })

    # Check 8: Directional totals Phase 59 vs Phase 61
    directional_59 = (
        p59.groupby("trade_direction")["value_change_trillion_yen"].sum()
    )

    directional_61 = (
        p61.groupby("trade_direction")["total_change_trillion_yen"].sum()
    )

    directional_rows = []

    for direction in sorted(set(directional_59.index) | set(directional_61.index)):
        value_59 = float(directional_59.get(direction, 0.0))
        value_61 = float(directional_61.get(direction, 0.0))
        difference = value_59 - value_61

        directional_rows.append({
            "trade_direction": direction,
            "phase59_change_trillion_yen": value_59,
            "phase61_change_trillion_yen": value_61,
            "difference_trillion_yen": difference,
            "status": "PASS" if abs(difference) <= TOLERANCE else "FAIL",
        })

    directional_df = pd.DataFrame(directional_rows)
    directional_pass = (directional_df["status"] == "PASS").all()

    checks.append({
        "check": "Phase 59 vs Phase 61 export/import totals",
        "max_abs_difference_trillion_yen": float(
            directional_df["difference_trillion_yen"].abs().max()
        ),
        "status": "PASS" if directional_pass else "FAIL",
    })

    # Save reconciliation details
    reconciliation_path = REPORTS / "65_semiconductor_cross_phase_reconciliation.csv"
    p59_p61.to_csv(reconciliation_path, index=False, encoding="utf-8-sig")

    directional_path = REPORTS / "65_semiconductor_directional_totals.csv"
    directional_df.to_csv(directional_path, index=False, encoding="utf-8-sig")

    checks_df = pd.DataFrame(checks)
    checks_path = REPORTS / "65_semiconductor_qa_checks.csv"
    checks_df.to_csv(checks_path, index=False, encoding="utf-8-sig")

    overall_pass = (checks_df["status"] == "PASS").all()

    summary_lines = [
        "PHASE 65 - SEMICONDUCTOR DASHBOARD QA",
        "",
        f"Phase 59 rows: {len(p59):,}",
        f"Phase 61 rows: {len(p61):,}",
        f"Phase 62 rows: {len(p62):,}",
        f"Phase 63 heatmap rows: {len(heatmap):,}",
        f"Phase 63 ranking rows: {len(ranking):,}",
        f"Expected heatmap rows: {expected_heatmap_rows:,}",
        "",
        "CHECK RESULTS",
    ]

    for item in checks:
        summary_lines.append(
            f"{item['status']}: {item['check']} "
            f"(max difference {item['max_abs_difference_trillion_yen']:.12f})"
        )

    summary_lines.extend([
        "",
        f"OVERALL: {'PASS' if overall_pass else 'FAIL'}",
        "",
        "Scope: HS6 854231, 854232, 854239; 2017 to 2020.",
        "Interpretation: descriptive trade-value changes, not causal estimates.",
    ])

    summary_path = REPORTS / "65_semiconductor_dashboard_qa_summary.txt"
    summary_path.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print("\nPHASE 65 QA RESULTS")
    print(checks_df.to_string(index=False))
    print(f"\nOverall: {'PASS' if overall_pass else 'FAIL'}")
    print(f"Summary: {summary_path}")
    print(f"Reconciliation: {reconciliation_path}")
    print(f"Directional totals: {directional_path}")
    print(f"Checks CSV: {checks_path}")

    if not overall_pass:
        raise SystemExit("Phase 65 QA failed. Review the report before proceeding.")

if __name__ == "__main__":
    main()
