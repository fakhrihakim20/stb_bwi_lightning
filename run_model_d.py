"""Run Model D end-to-end and append rows to outputs/forecast_2026_2030.parquet.

This script is invoked AFTER Model C has produced its forecast parquet (via
the notebook). It:

  1. Reads the tidy data and Model C's existing forecast parquet.
  2. Fits Model D with nested-LOYO-tuned hyperparameters on the full 7 years.
  3. Runs 200 bootstrap replicates × 3 scenarios to produce Model D's
     quantiles (count/density/mean_ka/max_ka × p50/lo80/hi80/lo95/hi95).
  4. Appends Model D rows (with model="D") to the existing forecast parquet.
  5. Writes outputs/forecast_climate_stamps.csv with provider/issued_date
     audit metadata per (year, scenario).
  6. Runs Model D LOYO + expanding-window CV and appends to cv_results.parquet.
  7. Computes Model D's selection-distribution table (how often half_life=
     ∞ vs 2/3/5 wins) and writes outputs/model_d_selection.csv.

Model C rows in outputs/forecast_2026_2030.parquet are NEVER modified.
"""

from __future__ import annotations

import json
import math
import os
import sys
import warnings
from pathlib import Path

# Force UTF-8 stdout on Windows (cp1252 console can't encode "∈ ∞ ⚠")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np
import pandas as pd

# Make src/ importable
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from src.recency import recency_weights, effective_n
from src.climate_forecast import (
    fetch_iri_enso_plume, fetch_cpc_enso_probs, fetch_bom_outlook,
    load_bmkg_manual, build_forecast_table, project_climate,
)
from src.models_d import fit_model_d, predict_model_d, model_d_bootstrap_one
from src.cv_d import cv_loyo_d, cv_expanding_d

DATA = HERE / "data_tidy"
CACHE = HERE / "cache"
OUT = HERE / "outputs"
N_BOOT = 200      # Model C uses 500; Model D uses 200 to keep wall-clock <10 min
RNG_SEED = 20260514


def jja_mean(df: pd.DataFrame, year: int) -> float:
    s = df[(df["year"] == year) & df["month"].between(6, 8)]["value"].dropna()
    if len(s):
        return float(s.mean())
    s = df[df["year"] == year]["value"].dropna()
    return float(s.mean()) if len(s) else 0.0


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)

    print("=== Loading tidy data ===")
    panel = pd.read_csv(DATA / "exposure_tower_year.csv")
    line_year_raw = pd.read_csv(DATA / "exposure_line_year.csv")
    towers = pd.read_csv(DATA / "towers.csv")
    nino = pd.read_parquet(CACHE / "nino34.parquet")
    dmi  = pd.read_parquet(CACHE / "dmi.parquet")
    elev_df = pd.read_parquet(CACHE / "elevation.parquet")
    elev = elev_df.set_index("tower_id")["elev_m"]
    print(f"  panel {panel.shape}; line_year {line_year_raw.shape}; towers {len(towers)}")

    # Model C fits Stage 1 on the PANEL-AGGREGATE annual total (≈5× the
    # line-unique total because each strike is counted by ~5 adjacent towers'
    # 3.125 km² circles — known Vaisala over-counting, documented in
    # CHANGELOG.md). We mirror that convention so Model D's outputs land on
    # the same per-tower scale as Model C's.
    line_year = (panel.groupby("year")
                       .agg(count=("count", "sum"),
                            mean_ka=("mean_ka", "mean"),
                            max_ka=("max_ka", "max"),
                            density=("density", "sum"))
                       .reset_index())
    line_year["nino34_jja"] = line_year["year"].map(lambda y: jja_mean(nino, y))
    line_year["dmi_jja"]    = line_year["year"].map(lambda y: jja_mean(dmi, y))
    panel = panel.merge(
        line_year[["year", "nino34_jja", "dmi_jja", "mean_ka", "max_ka"]]
            .rename(columns={"mean_ka": "_line_mean_ka", "max_ka": "_line_max_ka"}),
        on="year", how="left",
    )
    # Use observed per-tower mean_ka/max_ka (from panel)
    # If absent (rare), fall back to line-level
    if "mean_ka" not in panel.columns or panel["mean_ka"].isna().all():
        panel["mean_ka"] = panel["_line_mean_ka"]
    if "max_ka" not in panel.columns or panel["max_ka"].isna().all():
        panel["max_ka"] = panel["_line_max_ka"]

    # Distance to coast (Bali Strait anchor)
    bali_strait = (-8.16, 114.42)
    def haversine(lat, lng):
        R = 6371.0
        lat1, lat2 = math.radians(bali_strait[0]), math.radians(lat)
        dlat = lat2 - lat1
        dlng = math.radians(lng - bali_strait[1])
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlng/2)**2
        return 2 * R * math.asin(math.sqrt(a))
    towers["dist_coast"] = [haversine(r["lat"], r["lng"]) for _, r in towers.iterrows()]
    dist_coast = towers.set_index("tower_id")["dist_coast"]

    print("\n=== Loading / building forecast climate table ===")
    iri = fetch_iri_enso_plume(CACHE)
    cpc = fetch_cpc_enso_probs(CACHE)
    bom = fetch_bom_outlook(CACHE)
    bmkg = load_bmkg_manual(CACHE / "bmkg_outlook.csv")
    forecast_table = build_forecast_table(
        [iri, cpc, bom, bmkg],
        cache_path=CACHE / "forecast_climate.parquet",
    )
    print(f"  forecast_table rows: {len(forecast_table)}; "
          f"providers: {forecast_table['provider'].unique().tolist()}")

    # Build per-year, per-scenario projected climate for 2026-2030
    print("\n=== Projecting climate per (year, scenario) ===")
    forecast_years = [2026, 2027, 2028, 2029, 2030]
    scenarios = ["LaNina", "Neutral", "ElNino"]
    stamps_rows = []
    climate_future = []
    for yr in forecast_years:
        for sc in scenarios:
            p = project_climate(yr, forecast_table, scenario=sc, issue_year=2026)
            climate_future.append(p)
            stamps_rows.append(p)
    climate_future = pd.DataFrame(climate_future)
    stamps = pd.DataFrame(stamps_rows)
    stamps_path = OUT / "forecast_climate_stamps.csv"
    stamps.to_csv(stamps_path, index=False)
    print(f"  wrote {stamps_path} ({len(stamps)} rows)")

    print("\n=== Tuning hyperparameters (nested LOYO) ===")
    print("  (LOYO over half_life in {2,3,5,inf} x ridge in {1,10,100})")
    from src.cv_d import tune_hyperparameters
    tuned = tune_hyperparameters(panel, line_year, towers,
                                  elev=elev, dist_coast=dist_coast)
    hl  = tuned["best_half_life"]
    ra  = tuned["best_ridge_alpha"]
    print(f"  Selected: half_life={hl}  ridge_alpha={ra}")
    print(f"  Top 3 grid:")
    print(tuned["inner_scores"].head(3).to_string(index=False))

    print("\n=== Fitting final Model D on all 7 years ===")
    fit_full = fit_model_d(panel, line_year, towers,
                            half_life=hl, ridge_alpha=ra,
                            elev=elev, dist_coast=dist_coast)
    print(f"  Selected count formula: {fit_full.count_formula}")
    print(f"  Selected mean_ka formula: {fit_full.mean_ka_formula}")
    print(f"  Selected max_ka formula: {fit_full.max_ka_formula}")
    print(f"  Effective n: {fit_full.n_eff:.3f}")
    print(f"  Notes: {fit_full.notes or '(none)'}")

    reverted = fit_full.is_reverted_to_c
    if reverted:
        print("\n  !! Model D collapsed to a JS-shrunk climatology "
              "(no recency / climate skill). Outputs will be flagged with "
              "notes='reverted_to_C_no_recency_skill'.")

    print("\n=== Running bootstrap (n={}) × {} scenarios ===".format(
        N_BOOT, len(scenarios)))
    all_samples = []
    for sc in scenarios:
        sc_climate = climate_future[climate_future["scenario"] == sc].copy()
        for b in range(N_BOOT):
            sample = model_d_bootstrap_one(
                panel, line_year, towers, sc_climate,
                half_life=hl, ridge_alpha=ra,
                elev=elev, dist_coast=dist_coast,
                rng=np.random.default_rng(RNG_SEED + b * 7 + hash(sc) % 100),
            )
            sample["_b"] = b
            all_samples.append(sample)
        print(f"  {sc}: {N_BOOT} reps done")
    boot_df = pd.concat(all_samples, ignore_index=True)
    print(f"  bootstrap rows total: {len(boot_df):,}")

    print("\n=== Quantile aggregation ===")
    def qsum(group):
        return pd.Series({
            "count_p50":   group["count_sample"].quantile(0.50),
            "count_lo80":  group["count_sample"].quantile(0.10),
            "count_hi80":  group["count_sample"].quantile(0.90),
            "count_lo95":  group["count_sample"].quantile(0.025),
            "count_hi95":  group["count_sample"].quantile(0.975),
            "density_p50": group["density_sample"].quantile(0.50),
            "density_lo80": group["density_sample"].quantile(0.10),
            "density_hi80": group["density_sample"].quantile(0.90),
            "density_lo95": group["density_sample"].quantile(0.025),
            "density_hi95": group["density_sample"].quantile(0.975),
            "mean_ka_p50":  group["mean_ka_sample"].quantile(0.50),
            "mean_ka_lo80": group["mean_ka_sample"].quantile(0.10),
            "mean_ka_hi80": group["mean_ka_sample"].quantile(0.90),
            "mean_ka_lo95": group["mean_ka_sample"].quantile(0.025),
            "mean_ka_hi95": group["mean_ka_sample"].quantile(0.975),
            "max_ka_p50":   group["max_ka_sample"].quantile(0.50),
            "max_ka_lo80":  group["max_ka_sample"].quantile(0.10),
            "max_ka_hi80":  group["max_ka_sample"].quantile(0.90),
            "max_ka_lo95":  group["max_ka_sample"].quantile(0.025),
            "max_ka_hi95":  group["max_ka_sample"].quantile(0.975),
        })
    summary = (boot_df.groupby(["tower_id", "year", "scenario"])
                       .apply(qsum)
                       .reset_index())
    summary["model"] = "D"

    # Attach climate metadata
    summary = summary.merge(
        stamps[["year", "scenario", "provider", "issued_date",
                "confidence", "fallback_status", "source", "lead_months"]],
        on=["year", "scenario"], how="left",
    )
    summary["notes"] = fit_full.notes

    # Compute Marginalized (mean across scenarios)
    marg = (summary.groupby(["tower_id", "year"])
                     [["count_p50","count_lo80","count_hi80","count_lo95","count_hi95",
                       "density_p50","density_lo80","density_hi80","density_lo95","density_hi95",
                       "mean_ka_p50","mean_ka_lo80","mean_ka_hi80","mean_ka_lo95","mean_ka_hi95",
                       "max_ka_p50","max_ka_lo80","max_ka_hi80","max_ka_lo95","max_ka_hi95"]]
                     .mean().reset_index())
    marg["scenario"] = "Marginalized"
    marg["model"] = "D"
    marg["provider"] = "marginalized"
    marg["issued_date"] = pd.Timestamp.utcnow().normalize()
    marg["confidence"] = "low"
    marg["fallback_status"] = True
    marg["source"] = "scenario_average"
    marg["lead_months"] = pd.NA
    marg["notes"] = fit_full.notes
    model_d_rows = pd.concat([summary, marg], ignore_index=True)
    print(f"  Model D rows: {len(model_d_rows)}")

    # Save Model D summary table separately for transparency
    model_d_path = OUT / "model_d_forecast.parquet"
    model_d_rows.to_parquet(model_d_path)
    print(f"  wrote {model_d_path}")

    # ------- Append to forecast_2026_2030.parquet ----------------------
    print("\n=== Appending Model D rows to forecast_2026_2030.parquet ===")
    fc_path = OUT / "forecast_2026_2030.parquet"
    fc_existing = pd.read_parquet(fc_path)
    if "model" not in fc_existing.columns:
        fc_existing["model"] = "C"
    # Strip prior Model D rows if any (idempotent rerun)
    fc_keep = fc_existing[fc_existing["model"] == "C"].copy()
    print(f"  Model C rows preserved: {len(fc_keep)}")

    # Align columns
    keep_cols = ["tower_id","year","scenario","model",
                 "count_p50","count_lo80","count_hi80","count_lo95","count_hi95",
                 "density_p50","density_lo80","density_hi80","density_lo95","density_hi95",
                 "mean_ka_p50","mean_ka_lo80","mean_ka_hi80","mean_ka_lo95","mean_ka_hi95",
                 "max_ka_p50","max_ka_lo80","max_ka_hi80","max_ka_lo95","max_ka_hi95"]
    for c in keep_cols:
        if c not in fc_keep.columns:
            fc_keep[c] = pd.NA
        if c not in model_d_rows.columns:
            model_d_rows[c] = pd.NA
    combined = pd.concat([fc_keep[keep_cols], model_d_rows[keep_cols]], ignore_index=True)
    combined.to_parquet(fc_path)
    print(f"  wrote {fc_path}  (total rows: {len(combined)}; "
          f"C: {(combined['model']=='C').sum()}, D: {(combined['model']=='D').sum()})")

    # ------- Cross-validation ----------------------
    print("\n=== Running Model D LOYO CV (with nested hyperparameter tuning) ===")
    print("  This is the slow step; ~7 outer folds × 12 inner combinations × 6 inner folds")
    cv_loyo = cv_loyo_d(panel, line_year, towers,
                        elev=elev, dist_coast=dist_coast, nested=True)
    print(f"  LOYO CV rows: {len(cv_loyo)}")

    print("\n=== Running Model D expanding-window CV ===")
    cv_exp = cv_expanding_d(panel, line_year, towers,
                            elev=elev, dist_coast=dist_coast)
    print(f"  Expanding CV rows: {len(cv_exp)}")

    # Selection distribution
    sel_rows = pd.concat([cv_loyo, cv_exp], ignore_index=True)
    sel_summary = (sel_rows.dropna(subset=["half_life"])
                          .groupby("half_life").size()
                          .reset_index(name="n_folds_selected"))
    sel_summary.to_csv(OUT / "model_d_selection.csv", index=False)
    print(f"  Selection distribution:")
    print(sel_summary.to_string(index=False))

    # Append to cv_results
    print("\n=== Appending Model D rows to cv_results.parquet ===")
    cv_path = OUT / "cv_results.parquet"
    cv_existing = pd.read_parquet(cv_path)
    # Filter prior D rows for idempotency
    cv_existing_keep = cv_existing[cv_existing["model"] != "D"].copy()
    for c in cv_existing.columns:
        if c not in cv_loyo.columns:
            cv_loyo[c] = pd.NA
        if c not in cv_exp.columns:
            cv_exp[c] = pd.NA
    # Need to add half_life, ridge_alpha columns to existing if absent
    if "half_life" not in cv_existing_keep.columns:
        cv_existing_keep["half_life"] = pd.NA
    if "ridge_alpha" not in cv_existing_keep.columns:
        cv_existing_keep["ridge_alpha"] = pd.NA

    all_cv = pd.concat(
        [cv_existing_keep, cv_loyo, cv_exp],
        ignore_index=True, sort=False,
    )
    all_cv.to_parquet(cv_path)
    print(f"  wrote {cv_path}  (rows: {len(all_cv)}; "
          f"models: {all_cv['model'].value_counts().to_dict()})")

    # ------- Audit summary ----------------------
    print("\n=== Audit summary ===")
    print(f"  Model D half_life selected (final): {hl}")
    print(f"  Model D ridge_alpha selected (final): {ra}")
    print(f"  Reverted to C (no recency skill): {reverted}")
    print(f"  Forecast climate provider: {forecast_table['provider'].iloc[0]}")
    print(f"  All Model D rows fallback_status=True: "
          f"{(model_d_rows['fallback_status']==True).all()}")
    print(f"  Share invariant (Σ shares ≈ 1 per scenario per year): "
          f"checking...")
    bad_shares = []
    for (yr, sc), g in summary.groupby(["year", "scenario"]):
        s_count = (g["count_p50"].sum() / max(g["count_p50"].sum(), 1e-9))
        # Share invariance is per-fit; the predicted counts already incorporate
        # shares*line_total so the sum is line_total, not 1. Verify shares sum
        # of the underlying fit instead:
        pass
    print(f"  fit_full.shares_count.sum() = {fit_full.shares_count.sum():.6f} (target 1.0)")
    print(f"  fit_full.shares_density.sum() = {fit_full.shares_density.sum():.6f} (target 1.0)")

    print("\n[OK] Model D run complete.")


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    # Suppress statsmodels' PerfectSeparationWarning — expected at n=7 when
    # we evaluate over-parameterised candidates; AICc correctly rejects them.
    try:
        from statsmodels.tools.sm_exceptions import PerfectSeparationWarning
        warnings.filterwarnings("ignore", category=PerfectSeparationWarning)
    except Exception:
        pass
    main()
