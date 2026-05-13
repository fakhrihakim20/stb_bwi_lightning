"""Generate JSON data files for the static report website.

Reads:  data_tidy/*.csv, outputs/forecast_2026_2030.parquet, cache/nino34.parquet
Writes: website/figures/*.json  (consumed by website/assets/charts.js)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data_tidy"
OUT  = HERE / "outputs"
CACHE = HERE / "cache"
WEB = HERE / "website"
FIG = WEB / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def write_json(name: str, payload: dict) -> None:
    path = FIG / f"{name}.json"
    path.write_text(json.dumps(payload, allow_nan=False, default=float))
    print(f"  wrote {path.relative_to(HERE)}  ({path.stat().st_size:,} bytes)")


# ---------------------------------------------------------------------------
# 1. Historical line totals + ENSO/IOD overlay
# ---------------------------------------------------------------------------
line_year = pd.read_csv(DATA / "exposure_line_year.csv")
panel = pd.read_csv(DATA / "exposure_tower_year.csv")
nino  = pd.read_parquet(CACHE / "nino34.parquet")
dmi   = pd.read_parquet(CACHE / "dmi.parquet")


def jja_mean(df: pd.DataFrame, year: int) -> float:
    s = df[(df["year"] == year) & df["month"].between(6, 8)]["value"].dropna()
    if len(s):
        return float(s.mean())
    # fallback to whole-year mean
    s = df[df["year"] == year]["value"].dropna()
    return float(s.mean()) if len(s) else 0.0


years = sorted(line_year["year"].unique())
write_json("hist_overview", {
    "years": years,
    "unique_strikes": [int(line_year.loc[line_year["year"] == y, "count"].iloc[0]) for y in years],
    "gfd_ieee1410": [round(float(line_year.loc[line_year["year"] == y, "density"].iloc[0]), 3) for y in years],
    "panel_sum":   [int(panel.loc[panel["year"] == y, "count"].sum()) for y in years],
    "panel_density_mean": [round(float(panel.loc[panel["year"] == y, "density"].mean()), 3) for y in years],
    "nino34_jja": [round(jja_mean(nino, y), 3) for y in years],
    "dmi_jja":    [round(jja_mean(dmi, y), 3) for y in years],
})

# ---------------------------------------------------------------------------
# 2. Forecast 2026–2030 by scenario
# ---------------------------------------------------------------------------
fc = pd.read_parquet(OUT / "forecast_2026_2030.parquet")
towers = pd.read_csv(DATA / "towers.csv")

scenarios = ["LaNina", "Neutral", "ElNino"]
scenario_summary = {}
for sc in scenarios + ["Marginalized"]:
    sub = fc[fc["scenario"] == sc]
    agg = (sub.groupby("year")
              .agg(density_p50=("density_p50","mean"),
                   density_lo80=("density_lo80","mean"),
                   density_hi80=("density_hi80","mean"),
                   density_lo95=("density_lo95","mean"),
                   density_hi95=("density_hi95","mean"))
              .reset_index())
    scenario_summary[sc] = {
        "year":       agg["year"].astype(int).tolist(),
        "p50":        [round(v, 3) for v in agg["density_p50"]],
        "lo80":       [round(v, 3) for v in agg["density_lo80"]],
        "hi80":       [round(v, 3) for v in agg["density_hi80"]],
        "lo95":       [round(v, 3) for v in agg["density_lo95"]],
        "hi95":       [round(v, 3) for v in agg["density_hi95"]],
    }
write_json("forecast_scenarios", scenario_summary)

# ---------------------------------------------------------------------------
# 3. Top 20 ranking by 5-year mean GFD (Neutral)
# ---------------------------------------------------------------------------
top20 = (fc.query("scenario == 'Neutral'")
            .groupby("tower_id")
            .agg(p50=("density_p50","mean"),
                 lo80=("density_lo80","mean"),
                 hi80=("density_hi80","mean"))
            .reset_index()
            .merge(towers, on="tower_id")
            .sort_values("p50", ascending=False)
            .head(20))
write_json("top20", {
    "tower_id":  top20["tower_id"].astype(int).tolist(),
    "p50":       [round(v, 2) for v in top20["p50"]],
    "lo80":      [round(v, 2) for v in top20["lo80"]],
    "hi80":      [round(v, 2) for v in top20["hi80"]],
    "lat":       [round(v, 5) for v in top20["lat"]],
    "lng":       [round(v, 5) for v in top20["lng"]],
})

# ---------------------------------------------------------------------------
# 4. Map data — all 281 towers with 5-year mean Neutral density + scenarios
# ---------------------------------------------------------------------------
map_5yr = (fc.query("scenario in ['LaNina','Neutral','ElNino']")
              .groupby(["tower_id","scenario"])
              .agg(p50=("density_p50","mean"),
                   lo80=("density_lo80","mean"),
                   hi80=("density_hi80","mean"))
              .reset_index()
              .pivot(index="tower_id", columns="scenario", values=["p50","lo80","hi80"]))
map_5yr.columns = [f"{a}_{b}" for a, b in map_5yr.columns]
map_5yr = map_5yr.reset_index().merge(towers, on="tower_id")

# Try to merge elevation if cached
elev_cache = CACHE / "elevation.parquet"
if elev_cache.exists():
    elev = pd.read_parquet(elev_cache)
    map_5yr = map_5yr.merge(elev, on="tower_id", how="left")
else:
    map_5yr["elev_m"] = 0.0

write_json("map_towers", {
    "towers": [
        {
            "id": int(r["tower_id"]),
            "lat": round(r["lat"], 5),
            "lng": round(r["lng"], 5),
            "elev": int(r.get("elev_m", 0) or 0),
            "lanina": round(r["p50_LaNina"], 2),
            "neutral": round(r["p50_Neutral"], 2),
            "elnino": round(r["p50_ElNino"], 2),
            "lo80": round(r["lo80_Neutral"], 2),
            "hi80": round(r["hi80_Neutral"], 2),
        }
        for _, r in map_5yr.iterrows()
    ],
    "line_path": [[round(r["lat"], 5), round(r["lng"], 5)]
                  for _, r in towers.sort_values("tower_id").iterrows()],
})

# ---------------------------------------------------------------------------
# 5. Monthly seasonality (line-aggregate, averaged across years)
# ---------------------------------------------------------------------------
monthly = pd.read_csv(DATA / "monthly_line.csv", parse_dates=["period_start"])
# NOTE: do NOT filter by is_partial_month here — tidy_data.py flags all December
# rows as partial (trailing export period) but they are real full-month observations.
# Filtering would silently drop December from every year.
monthly["month"] = monthly["period_start"].dt.month
season = (monthly.groupby("month")["count"]
                  .agg(["mean", "std", "count"])
                  .reset_index()
                  .rename(columns={"mean":"avg","std":"sd","count":"n"}))
write_json("seasonality", {
    "month": season["month"].astype(int).tolist(),
    "mean":  [round(v, 1) for v in season["avg"]],
    "sd":    [round(v if pd.notna(v) else 0, 1) for v in season["sd"]],
    "n":     season["n"].astype(int).tolist(),
})

# ---------------------------------------------------------------------------
# 6. CV skill table
# ---------------------------------------------------------------------------
cv = pd.read_parquet(OUT / "cv_results.parquet")
cv_summary = (cv.groupby(["scheme","target","model"])
                [["MAE","RMSE","Deviance","CRPS"]].mean().reset_index())
write_json("cv_skill", {
    "rows": [
        {
            "scheme":   r["scheme"],
            "target":   r["target"],
            "model":    r["model"],
            "MAE":      round(float(r["MAE"]), 3),
            "RMSE":     round(float(r["RMSE"]), 3),
            "Deviance": round(float(r["Deviance"]), 1),
            "CRPS":     round(float(r["CRPS"]), 3),
        }
        for _, r in cv_summary.iterrows()
    ]
})

# ---------------------------------------------------------------------------
# 7. Per-tower full forecast (for searchable table)
# ---------------------------------------------------------------------------
per_tower = (fc.query("scenario == 'Neutral'")
                .merge(towers[["tower_id","lat","lng"]], on="tower_id"))
write_json("per_tower", {
    "rows": [
        {
            "tower":   int(r["tower_id"]),
            "year":    int(r["year"]),
            "lat":     round(r["lat"], 5),
            "lng":     round(r["lng"], 5),
            "p50":     round(float(r["density_p50"]), 2),
            "lo80":    round(float(r["density_lo80"]), 2),
            "hi80":    round(float(r["density_hi80"]), 2),
            "count":   round(float(r["count_p50"]), 1),
        }
        for _, r in per_tower.iterrows()
    ]
})

print("\nAll figure JSONs written.")
