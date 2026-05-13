"""Generate JSON data files for the static report website.

Reads:  data_tidy/*.csv, outputs/forecast_2026_2030.parquet, cache/*.parquet,
        outputs/cv_results.parquet, outputs/forecast_climate_stamps.csv,
        outputs/model_d_selection.csv
Writes: docs/figures/*.json  (consumed by docs/assets/charts.js)

Model awareness:
    The forecast parquet now carries a `model` column ∈ {"C", "D"}.
    - Existing JSONs (forecast_scenarios.json, top20.json, map_towers.json,
      tower_gfd_profile.json, per_tower.json) keep their pre-Model-D schema
      and are filtered to Model C rows only — preserving backward compatibility
      for the live site.
    - Parallel JSONs with the _d suffix (forecast_scenarios_d.json, etc.)
      carry the Model D data with the same schema.
    - New comparison JSONs (comparison_skill.json, comparison_delta.json,
      comparison_top20.json, model_d_meta.json) feed the new Model C vs
      Model D section.
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
DOCS = HERE / "docs"
FIG = DOCS / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def write_json(name: str, payload: dict) -> None:
    path = FIG / f"{name}.json"
    path.write_text(json.dumps(payload, allow_nan=False, default=str))
    print(f"  wrote {path.relative_to(HERE)}  ({path.stat().st_size:,} bytes)")


def jja_mean(df: pd.DataFrame, year: int) -> float:
    s = df[(df["year"] == year) & df["month"].between(6, 8)]["value"].dropna()
    if len(s):
        return float(s.mean())
    s = df[df["year"] == year]["value"].dropna()
    return float(s.mean()) if len(s) else 0.0


# ---------------------------------------------------------------------------
# Load inputs once
# ---------------------------------------------------------------------------
print("Loading inputs...")
line_year = pd.read_csv(DATA / "exposure_line_year.csv")
panel = pd.read_csv(DATA / "exposure_tower_year.csv")
towers = pd.read_csv(DATA / "towers.csv")
nino  = pd.read_parquet(CACHE / "nino34.parquet")
dmi   = pd.read_parquet(CACHE / "dmi.parquet")
fc    = pd.read_parquet(OUT / "forecast_2026_2030.parquet")
if "model" not in fc.columns:
    fc["model"] = "C"
print(f"  forecast rows: {len(fc):,} "
      f"(C: {(fc['model']=='C').sum():,}, D: {(fc['model']=='D').sum():,})")

elev_cache = CACHE / "elevation.parquet"
elev = pd.read_parquet(elev_cache) if elev_cache.exists() else None

# ---------------------------------------------------------------------------
# 1. Historical line totals + ENSO/IOD overlay (unchanged)
# ---------------------------------------------------------------------------
years = sorted(line_year["year"].unique())
write_json("hist_overview", {
    "years": years,
    "unique_strikes": [int(line_year.loc[line_year["year"] == y, "count"].iloc[0]) for y in years],
    "gfd_ieee1410":   [round(float(line_year.loc[line_year["year"] == y, "density"].iloc[0]), 3) for y in years],
    "panel_sum":      [int(panel.loc[panel["year"] == y, "count"].sum()) for y in years],
    "panel_density_mean": [round(float(panel.loc[panel["year"] == y, "density"].mean()), 3) for y in years],
    "nino34_jja": [round(jja_mean(nino, y), 3) for y in years],
    "dmi_jja":    [round(jja_mean(dmi, y), 3) for y in years],
})


# ---------------------------------------------------------------------------
# 2. Forecast 2026–2030 by scenario — per model
# ---------------------------------------------------------------------------
scenarios = ["LaNina", "Neutral", "ElNino", "Marginalized"]


def build_scenario_summary(model_label: str) -> dict:
    out = {}
    sub_all = fc[fc["model"] == model_label]
    for sc in scenarios:
        sub = sub_all[sub_all["scenario"] == sc]
        if sub.empty:
            continue
        agg = (sub.groupby("year")
                  .agg(density_p50=("density_p50","mean"),
                       density_lo80=("density_lo80","mean"),
                       density_hi80=("density_hi80","mean"),
                       density_lo95=("density_lo95","mean"),
                       density_hi95=("density_hi95","mean"))
                  .reset_index())
        out[sc] = {
            "year": agg["year"].astype(int).tolist(),
            "p50":  [round(v, 3) for v in agg["density_p50"]],
            "lo80": [round(v, 3) for v in agg["density_lo80"]],
            "hi80": [round(v, 3) for v in agg["density_hi80"]],
            "lo95": [round(v, 3) for v in agg["density_lo95"]],
            "hi95": [round(v, 3) for v in agg["density_hi95"]],
        }
    return out


# Model C (legacy schema, unchanged)
write_json("forecast_scenarios", build_scenario_summary("C"))
# Model D (parallel schema)
if (fc["model"] == "D").any():
    write_json("forecast_scenarios_d", build_scenario_summary("D"))


# ---------------------------------------------------------------------------
# 3. Top-20 ranking by 5-yr mean GFD (Neutral) — per model
# ---------------------------------------------------------------------------
def build_top20(model_label: str) -> dict:
    sub = fc[(fc["model"] == model_label) & (fc["scenario"] == "Neutral")]
    if sub.empty:
        return {"tower_id": [], "p50": [], "lo80": [], "hi80": [],
                "lat": [], "lng": []}
    t20 = (sub.groupby("tower_id")
              .agg(p50=("density_p50","mean"),
                   lo80=("density_lo80","mean"),
                   hi80=("density_hi80","mean"))
              .reset_index()
              .merge(towers[["tower_id", "lat", "lng"]], on="tower_id")
              .sort_values("p50", ascending=False)
              .head(20))
    return {
        "tower_id":  t20["tower_id"].astype(int).tolist(),
        "p50":  [round(v, 2) for v in t20["p50"]],
        "lo80": [round(v, 2) for v in t20["lo80"]],
        "hi80": [round(v, 2) for v in t20["hi80"]],
        "lat":  [round(v, 5) for v in t20["lat"]],
        "lng":  [round(v, 5) for v in t20["lng"]],
    }


write_json("top20", build_top20("C"))
if (fc["model"] == "D").any():
    write_json("top20_d", build_top20("D"))


# ---------------------------------------------------------------------------
# 4. Map data — 281 towers × 3 scenarios (5-yr mean) per model
# ---------------------------------------------------------------------------
def build_map_towers(model_label: str) -> dict:
    sub = fc[fc["model"] == model_label]
    sub = sub[sub["scenario"].isin(["LaNina", "Neutral", "ElNino"])]
    if sub.empty:
        return {"towers": [], "line_path": []}
    map_5yr = (sub.groupby(["tower_id", "scenario"])
                  .agg(p50=("density_p50","mean"),
                       lo80=("density_lo80","mean"),
                       hi80=("density_hi80","mean"))
                  .reset_index()
                  .pivot(index="tower_id", columns="scenario",
                         values=["p50","lo80","hi80"]))
    map_5yr.columns = [f"{a}_{b}" for a, b in map_5yr.columns]
    map_5yr = map_5yr.reset_index().merge(towers[["tower_id","lat","lng"]],
                                            on="tower_id")
    if elev is not None:
        map_5yr = map_5yr.merge(elev, on="tower_id", how="left")
    else:
        map_5yr["elev_m"] = 0.0

    out_towers = []
    for _, r in map_5yr.iterrows():
        out_towers.append({
            "id": int(r["tower_id"]),
            "lat": round(r["lat"], 5),
            "lng": round(r["lng"], 5),
            "elev": int(r.get("elev_m", 0) or 0),
            "lanina":  round(r.get("p50_LaNina", 0), 2),
            "neutral": round(r.get("p50_Neutral", 0), 2),
            "elnino":  round(r.get("p50_ElNino", 0), 2),
            "lo80":    round(r.get("lo80_Neutral", 0), 2),
            "hi80":    round(r.get("hi80_Neutral", 0), 2),
        })
    return {
        "towers": out_towers,
        "line_path": [[round(r["lat"], 5), round(r["lng"], 5)]
                      for _, r in towers.sort_values("tower_id").iterrows()],
    }


write_json("map_towers", build_map_towers("C"))
if (fc["model"] == "D").any():
    write_json("map_towers_d", build_map_towers("D"))


# ---------------------------------------------------------------------------
# 5. Monthly seasonality (unchanged from the December-fix commit)
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
# 6. CV skill — now with Model D rows
# ---------------------------------------------------------------------------
cv = pd.read_parquet(OUT / "cv_results.parquet")
agg_cols = [c for c in ["MAE","RMSE","Deviance","CRPS"] if c in cv.columns]
cv_summary = (cv.groupby(["scheme","target","model"])[agg_cols]
                .mean().reset_index())
rows = []
for _, r in cv_summary.iterrows():
    row = {
        "scheme":   str(r["scheme"]),
        "target":   str(r["target"]),
        "model":    str(r["model"]),
    }
    for c in agg_cols:
        v = r[c]
        row[c] = None if pd.isna(v) else round(float(v), 3)
    rows.append(row)
write_json("cv_skill", {"rows": rows})


# ---------------------------------------------------------------------------
# 7. Per-tower full forecast (searchable table) — per model (C only for now,
#    Model D version surfaced through model_d_meta + comparison JSONs)
# ---------------------------------------------------------------------------
per_tower = (fc.query("scenario == 'Neutral' and model == 'C'")
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


# ---------------------------------------------------------------------------
# 8. Tower-by-tower historical + forecast profile (used by Figure 3) — per model
# ---------------------------------------------------------------------------
def build_profile(model_label: str) -> dict:
    hist = panel[["tower_id","year","density"]]
    tower_ids = sorted(hist["tower_id"].unique().tolist())
    historical = {}
    for yr in sorted(hist["year"].unique()):
        row = hist[hist["year"] == yr].sort_values("tower_id")
        historical[str(int(yr))] = [round(float(v), 2) for v in row["density"].values]

    forecast = {}
    sub = fc[fc["model"] == model_label]
    for sc in ["LaNina","Neutral","ElNino","Marginalized"]:
        sub_sc = sub[sub["scenario"] == sc]
        if sub_sc.empty:
            continue
        forecast[sc] = {}
        for yr in sorted(sub_sc["year"].unique()):
            row = sub_sc[sub_sc["year"] == yr].sort_values("tower_id")
            forecast[sc][str(int(yr))] = [round(float(v), 2) for v in row["density_p50"].values]

    return {
        "tower_ids": [int(t) for t in tower_ids],
        "historical": historical,
        "forecast": forecast,
    }


write_json("tower_gfd_profile", build_profile("C"))
if (fc["model"] == "D").any():
    write_json("tower_gfd_profile_d", build_profile("D"))


# ---------------------------------------------------------------------------
# 9. Comparison JSONs (only if Model D rows exist)
# ---------------------------------------------------------------------------
if (fc["model"] == "D").any():
    # 9a. Skill comparison — already in cv_skill.json, but extract a clean
    # comparison table targeting the Neutral scenario count/density.
    cv_compare = (cv.groupby(["model","scheme","target"])[agg_cols]
                     .mean().reset_index())
    write_json("comparison_skill", {
        "rows": [
            {**{"model": str(r["model"]), "scheme": str(r["scheme"]),
                "target": str(r["target"])},
             **{c: (None if pd.isna(r[c]) else round(float(r[c]), 3))
                for c in agg_cols}}
            for _, r in cv_compare.iterrows()
        ]
    })

    # 9b. Line-level density mean per (year, scenario), Model C vs D ribbon
    def _ribbon(model_label):
        sub = fc[(fc["model"] == model_label) &
                 (fc["scenario"].isin(["LaNina","Neutral","ElNino","Marginalized"]))]
        agg = (sub.groupby(["year","scenario"])
                  .agg(p50=("density_p50","mean"),
                       lo80=("density_lo80","mean"),
                       hi80=("density_hi80","mean"))
                  .reset_index())
        out = {}
        for sc in ["LaNina","Neutral","ElNino","Marginalized"]:
            sa = agg[agg["scenario"] == sc].sort_values("year")
            out[sc] = {
                "year": sa["year"].astype(int).tolist(),
                "p50":  [round(v, 3) for v in sa["p50"]],
                "lo80": [round(v, 3) for v in sa["lo80"]],
                "hi80": [round(v, 3) for v in sa["hi80"]],
            }
        return out

    write_json("comparison_line", {
        "C": _ribbon("C"),
        "D": _ribbon("D"),
    })

    # 9c. Top-20 paired + Jaccard
    def _top_set(model_label):
        sub = fc[(fc["model"] == model_label) & (fc["scenario"] == "Neutral")]
        t = (sub.groupby("tower_id")["density_p50"].mean()
                 .sort_values(ascending=False).head(20))
        return t.index.tolist(), t.to_dict()

    ids_c, vals_c = _top_set("C")
    ids_d, vals_d = _top_set("D")
    both = set(ids_c) & set(ids_d)
    jaccard = len(both) / max(len(set(ids_c) | set(ids_d)), 1)
    union_ids = sorted(set(ids_c) | set(ids_d))
    write_json("comparison_top20", {
        "C_ids": [int(t) for t in ids_c],
        "D_ids": [int(t) for t in ids_d],
        "jaccard": round(jaccard, 3),
        "union_ids": [int(t) for t in union_ids],
        "C_values": {str(int(k)): round(float(v), 2) for k, v in vals_c.items()},
        "D_values": {str(int(k)): round(float(v), 2) for k, v in vals_d.items()},
    })

    # 9d. Per-tower delta D-C, Neutral scenario, 5-yr mean
    pivot = (fc.query("scenario == 'Neutral'")
                .groupby(["tower_id","model"])["density_p50"].mean()
                .unstack(fill_value=np.nan))
    if "C" in pivot.columns and "D" in pivot.columns:
        delta_df = pivot.reset_index()
        delta_df["delta"] = delta_df["D"] - delta_df["C"]
        delta_df = delta_df.merge(towers[["tower_id","lat","lng"]], on="tower_id")
        if elev is not None:
            delta_df = delta_df.merge(elev, on="tower_id", how="left")
        else:
            delta_df["elev_m"] = 0.0
        write_json("comparison_delta", {
            "rows": [
                {
                    "id": int(r["tower_id"]),
                    "lat": round(r["lat"], 5),
                    "lng": round(r["lng"], 5),
                    "elev": int(r.get("elev_m", 0) or 0),
                    "c": round(float(r["C"]), 2),
                    "d": round(float(r["D"]), 2),
                    "delta": round(float(r["delta"]), 2),
                }
                for _, r in delta_df.iterrows()
            ]
        })

    # 9e. Model D metadata — fallback, half_life, ridge, provider, notes
    stamps_path = OUT / "forecast_climate_stamps.csv"
    if stamps_path.exists():
        stamps = pd.read_csv(stamps_path)
    else:
        stamps = pd.DataFrame()

    sel_path = OUT / "model_d_selection.csv"
    sel = pd.read_csv(sel_path) if sel_path.exists() else pd.DataFrame()

    d_rows = fc[fc["model"] == "D"]
    notes_set = d_rows.get("notes", pd.Series(dtype=str)).dropna().unique().tolist()
    is_reverted = any("reverted_to_C" in str(n) for n in notes_set)

    fallback_status = d_rows.get("fallback_status", pd.Series(dtype=bool))
    all_fallback = bool(fallback_status.fillna(True).all()) if len(fallback_status) else True

    providers = d_rows.get("provider", pd.Series(dtype=str)).dropna().unique().tolist()

    write_json("model_d_meta", {
        "is_reverted_to_c": bool(is_reverted),
        "notes": list(map(str, notes_set)),
        "all_fallback": bool(all_fallback),
        "providers": list(map(str, providers)),
        "selection_distribution":
            sel.to_dict(orient="records") if not sel.empty else [],
        "climate_stamps":
            stamps.to_dict(orient="records") if not stamps.empty else [],
    })


print("\nAll figure JSONs written.")
