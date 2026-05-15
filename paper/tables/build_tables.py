"""Build the two paper tables from existing parquet/JSON outputs.

No new computation — every cell traces to a cell in outputs/cv_results.parquet
or outputs/forecast_2026_2030.parquet.

Outputs:
    tables/table1_cv_skill.csv          # raw numbers, machine-readable
    tables/table1_cv_skill.md           # markdown render for prose docs
    tables/table2_scenario_summary.csv
    tables/table2_scenario_summary.md
    tables/audit.csv                    # one row per quoted cell, with source
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = REPO / "outputs"
TARGET = HERE


def build_table1() -> tuple[pd.DataFrame, pd.DataFrame]:
    """CV skill matrix — A vs C vs D, count + density, LOYO + expanding.

    Source: outputs/cv_results.parquet
    Aggregation: groupby(scheme, target, model).mean() on MAE / RMSE / CRPS.
    """
    cv = pd.read_parquet(OUT / "cv_results.parquet")
    cv["scheme"] = cv["scheme"].astype(str).str.lower()
    metrics = ["MAE", "RMSE", "CRPS"]
    pivot = (cv.groupby(["scheme", "target", "model"])[metrics]
               .mean().reset_index())
    # Keep only count + density (kA targets out of paper scope)
    pivot = pivot[pivot["target"].isin(["count", "density"])].copy()
    pivot["scheme"] = pivot["scheme"].str.upper()
    pivot["model"] = pivot["model"].astype(str)
    # Pretty wide form for the paper: rows = (scheme, target, metric); cols = A/C/D
    long = pivot.melt(id_vars=["scheme", "target", "model"],
                      value_vars=metrics,
                      var_name="metric", value_name="value")
    wide = long.pivot_table(index=["scheme", "target", "metric"],
                            columns="model", values="value").reset_index()
    wide = wide[["scheme", "target", "metric", "A", "C", "D"]]
    # Round to 2 dp
    for c in ("A", "C", "D"):
        wide[c] = wide[c].round(2)
    return pivot, wide


def build_table2() -> pd.DataFrame:
    """2026 scenario summary — line-mean GFD per scenario, Model D.

    Source: outputs/forecast_2026_2030.parquet, model=='D', year==2026.
    Aggregation: mean across 281 towers of density_p50, density_lo80, density_hi80.
    """
    fc = pd.read_parquet(OUT / "forecast_2026_2030.parquet")
    sub = fc[(fc["model"] == "D") & (fc["year"] == 2026)]
    agg = (sub.groupby("scenario")
              .agg(density_p50=("density_p50", "mean"),
                   density_lo80=("density_lo80", "mean"),
                   density_hi80=("density_hi80", "mean"))
              .reset_index())
    # Order scenarios meaningfully
    order = {"LaNina": 0, "Neutral": 1, "ElNino": 2, "Marginalized": 3}
    agg["_order"] = agg["scenario"].map(order)
    agg = agg.sort_values("_order").drop(columns="_order").reset_index(drop=True)
    for c in ("density_p50", "density_lo80", "density_hi80"):
        agg[c] = agg[c].round(2)
    return agg


def write_markdown_table(df: pd.DataFrame, path: Path, caption: str) -> None:
    lines = [f"**{caption}**", ""]
    cols = df.columns.tolist()
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join("---" for _ in cols) + " |")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_audit() -> pd.DataFrame:
    """Audit rows — one per claim in the abstract / paper body."""
    rows = []
    cv = pd.read_parquet(OUT / "cv_results.parquet")
    cv["scheme"] = cv["scheme"].astype(str).str.lower()
    fc = pd.read_parquet(OUT / "forecast_2026_2030.parquet")

    # LOYO count RMSE per model
    for m in ("A", "C", "D"):
        sub = cv[(cv["scheme"] == "loyo") & (cv["target"] == "count") & (cv["model"] == m)]
        v = sub["RMSE"].mean()
        rows.append({
            "claim": f"Model {m} LOYO count RMSE",
            "value": round(v, 2),
            "source": "outputs/cv_results.parquet",
            "filter": f"scheme=='loyo' & target=='count' & model=='{m}'",
            "aggregation": "mean(RMSE) across folds",
        })

    # LOYO density RMSE per model
    for m in ("A", "C", "D"):
        sub = cv[(cv["scheme"] == "loyo") & (cv["target"] == "density") & (cv["model"] == m)]
        v = sub["RMSE"].mean()
        rows.append({
            "claim": f"Model {m} LOYO density RMSE",
            "value": round(v, 2),
            "source": "outputs/cv_results.parquet",
            "filter": f"scheme=='loyo' & target=='density' & model=='{m}'",
            "aggregation": "mean(RMSE) across folds",
        })

    # 2026 scenario means under Model D
    for sc in ("LaNina", "Neutral", "ElNino"):
        sub = fc[(fc["model"] == "D") & (fc["year"] == 2026) & (fc["scenario"] == sc)]
        v = sub["density_p50"].mean()
        rows.append({
            "claim": f"Model D 2026 {sc} line-mean density_p50",
            "value": round(v, 2),
            "source": "outputs/forecast_2026_2030.parquet",
            "filter": f"model=='D' & year==2026 & scenario=='{sc}'",
            "aggregation": "mean(density_p50) across 281 towers",
        })

    # Scenario spread (La Niña / El Niño) — computed from UNROUNDED means
    # so the spread does not inherit display-rounding error from the two
    # contributing rows above.
    la_raw = fc[(fc["model"] == "D") & (fc["year"] == 2026) & (fc["scenario"] == "LaNina")]["density_p50"].mean()
    el_raw = fc[(fc["model"] == "D") & (fc["year"] == 2026) & (fc["scenario"] == "ElNino")]["density_p50"].mean()
    rows.append({
        "claim": "Model D 2026 scenario spread (LaNina vs ElNino, %)",
        "value": round(100.0 * (la_raw - el_raw) / ((la_raw + el_raw) / 2.0), 1),
        "source": "outputs/forecast_2026_2030.parquet",
        "filter": "model=='D' & year==2026 & scenario in {'LaNina','ElNino'}",
        "aggregation": "100 * (LaNina - ElNino) / mean(LaNina, ElNino); from unrounded means",
    })

    # Top-20 Jaccard (from comparison_top20.json — already computed in generate_site_data.py)
    import json
    t20 = json.load(open(REPO / "docs" / "figures" / "comparison_top20.json"))
    rows.append({
        "claim": "Top-20 Jaccard overlap (Model C vs Model D)",
        "value": t20["jaccard"],
        "source": "docs/figures/comparison_top20.json",
        "filter": "key='jaccard'",
        "aggregation": "|C∩D| / |C∪D| on Neutral 5-yr mean top-20 towers",
    })

    # Per-tower 7-year mean density range (for the intro spatial-spread claim)
    panel = pd.read_csv(REPO / "data_tidy" / "exposure_tower_year.csv")
    by_tower = panel.groupby("tower_id")["density"].mean()
    rows.append({
        "claim": "Per-tower 7-yr mean density: min",
        "value": round(float(by_tower.min()), 2),
        "source": "data_tidy/exposure_tower_year.csv",
        "filter": "groupby(tower_id).mean(density)",
        "aggregation": "min across 281 tower-level means",
    })
    rows.append({
        "claim": "Per-tower 7-yr mean density: max",
        "value": round(float(by_tower.max()), 2),
        "source": "data_tidy/exposure_tower_year.csv",
        "filter": "groupby(tower_id).mean(density)",
        "aggregation": "max across 281 tower-level means",
    })
    rows.append({
        "claim": "Per-tower spatial ratio (max/min, 7-yr mean density)",
        "value": round(float(by_tower.max() / by_tower.min()), 2),
        "source": "data_tidy/exposure_tower_year.csv",
        "filter": "max/min of per-tower means",
        "aggregation": "ratio of max to min",
    })

    return pd.DataFrame(rows)


def main() -> None:
    pivot, wide = build_table1()
    pivot.to_csv(TARGET / "table1_cv_skill_long.csv", index=False)
    wide.to_csv(TARGET / "table1_cv_skill.csv", index=False)
    write_markdown_table(wide, TARGET / "table1_cv_skill.md",
                          caption="Table 1. Cross-validation skill of Models A, C, D "
                                  "on count and density targets (LOYO and expanding-window).")
    print(f"  wrote table1_cv_skill.csv  ({len(wide)} rows)")

    t2 = build_table2()
    t2.to_csv(TARGET / "table2_scenario_summary.csv", index=False)
    write_markdown_table(t2, TARGET / "table2_scenario_summary.md",
                          caption="Table 2. 2026 line-mean GFD forecast under Model D "
                                  "across three climate scenarios (mean across 281 towers).")
    print(f"  wrote table2_scenario_summary.csv  ({len(t2)} rows)")

    audit = build_audit()
    audit.to_csv(TARGET / "audit.csv", index=False)
    print(f"  wrote audit.csv  ({len(audit)} rows)")


if __name__ == "__main__":
    main()
