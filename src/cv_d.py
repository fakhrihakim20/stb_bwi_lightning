"""Nested leave-one-year-out cross-validation for Model D.

Outer LOYO holds year t*. For each outer fold:
  1. Inner LOYO over the remaining 6 years selects (half_life, ridge_alpha)
     by minimising mean inner-fold RMSE on count.
  2. Refit Model D with selected hyperparameters on all 6 training years.
  3. Predict year t* per-tower count/density; compute MAE/RMSE/Deviance/CRPS
     against observed.
  4. Report the distribution of selected hyperparameters across outer folds.

Hyperparameter grid (small on purpose — at n=7 we cannot afford fine search):
  half_life ∈ {2, 3, 5, ∞}
  ridge_alpha ∈ {1, 10, 100}

This module is intentionally independent of build_notebook.py so Model C's
CV harness is untouched.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd

from .models_d import fit_model_d, predict_model_d


__all__ = [
    "DEFAULT_HALF_LIFE_GRID",
    "DEFAULT_RIDGE_GRID",
    "tune_hyperparameters",
    "cv_loyo_d",
    "cv_expanding_d",
]


DEFAULT_HALF_LIFE_GRID = [2.0, 3.0, 5.0, math.inf]
DEFAULT_RIDGE_GRID = [1.0, 10.0, 100.0]


def _rmse(obs: np.ndarray, pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((obs - pred) ** 2)))


def _mae(obs: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs(obs - pred)))


def _poisson_deviance(obs: np.ndarray, pred: np.ndarray) -> float:
    pred = np.clip(pred, 1e-6, None)
    obs_clip = np.clip(obs, 1e-6, None)
    return float(2.0 * np.sum(obs * np.log(obs_clip / pred) - (obs - pred)))


def _gaussian_crps(obs: np.ndarray, pred: np.ndarray, sd: float | np.ndarray) -> float:
    """Closed-form CRPS for a Gaussian predictive distribution."""
    from scipy.stats import norm
    sd = np.asarray(sd, dtype=float)
    sd = np.clip(sd, 1e-3, None)
    z = (obs - pred) / sd
    return float(np.mean(sd * (z * (2 * norm.cdf(z) - 1) + 2 * norm.pdf(z) - 1.0 / np.sqrt(np.pi))))


def tune_hyperparameters(
    panel: pd.DataFrame,
    line_year: pd.DataFrame,
    towers: pd.DataFrame,
    *,
    elev: pd.Series | None = None,
    dist_coast: pd.Series | None = None,
    half_life_grid: Iterable[float] = DEFAULT_HALF_LIFE_GRID,
    ridge_grid: Iterable[float] = DEFAULT_RIDGE_GRID,
) -> dict:
    """Inner LOYO grid search for (half_life, ridge_alpha).

    Returns a dict with: ``best_half_life, best_ridge_alpha, inner_scores``.
    """
    years = sorted(line_year["year"].unique().tolist())
    grid_results = []

    for hl in half_life_grid:
        for ra in ridge_grid:
            fold_rmses = []
            for held in years:
                train_y = [y for y in years if y != held]
                p_tr = panel[panel["year"].isin(train_y)]
                l_tr = line_year[line_year["year"].isin(train_y)]
                try:
                    fit = fit_model_d(
                        p_tr, l_tr, towers,
                        half_life=hl, ridge_alpha=ra,
                        elev=elev, dist_coast=dist_coast,
                    )
                    # Predict the held year using its OBSERVED climate
                    # (perfect-forecast proxy — documented in the website caveat)
                    climate_held = line_year[line_year["year"] == held]
                    climate_in = pd.DataFrame([{
                        "year": held,
                        "scenario": "Neutral",
                        "nino34_jja": float(climate_held["nino34_jja"].iloc[0]),
                        "dmi_jja": float(climate_held["dmi_jja"].iloc[0]),
                    }])
                    pred = predict_model_d(fit, forecast_years=[held],
                                           climate_future=climate_in, towers=towers)
                    obs = (panel[panel["year"] == held]
                                 .set_index("tower_id")["count"])
                    pj = pred.set_index("tower_id")["count_p50"].reindex(obs.index)
                    fold_rmses.append(_rmse(obs.to_numpy(), pj.to_numpy()))
                except Exception:
                    fold_rmses.append(np.nan)

            mean_rmse = float(np.nanmean(fold_rmses)) if fold_rmses else float("inf")
            grid_results.append({
                "half_life": float(hl),
                "ridge_alpha": float(ra),
                "rmse": mean_rmse,
            })

    df = pd.DataFrame(grid_results).sort_values("rmse")
    if df.empty:
        return {"best_half_life": math.inf, "best_ridge_alpha": 10.0,
                "inner_scores": df}
    best = df.iloc[0]
    return {
        "best_half_life": float(best["half_life"]),
        "best_ridge_alpha": float(best["ridge_alpha"]),
        "inner_scores": df.reset_index(drop=True),
    }


def cv_loyo_d(
    panel: pd.DataFrame,
    line_year: pd.DataFrame,
    towers: pd.DataFrame,
    *,
    elev: pd.Series | None = None,
    dist_coast: pd.Series | None = None,
    nested: bool = True,
) -> pd.DataFrame:
    """Outer LOYO CV for Model D.

    Returns long-form DataFrame with columns:
        scheme, target, model, year_held, half_life, ridge_alpha,
        MAE, RMSE, Deviance, CRPS
    """
    years = sorted(line_year["year"].unique().tolist())
    rows = []

    for held in years:
        train_y = [y for y in years if y != held]
        p_tr = panel[panel["year"].isin(train_y)]
        l_tr = line_year[line_year["year"].isin(train_y)]

        if nested:
            tuned = tune_hyperparameters(p_tr, l_tr, towers,
                                          elev=elev, dist_coast=dist_coast)
            hl = tuned["best_half_life"]
            ra = tuned["best_ridge_alpha"]
        else:
            hl, ra = 3.0, 10.0

        try:
            fit = fit_model_d(p_tr, l_tr, towers,
                              half_life=hl, ridge_alpha=ra,
                              elev=elev, dist_coast=dist_coast)
            climate_held = line_year[line_year["year"] == held]
            climate_in = pd.DataFrame([{
                "year": held, "scenario": "Neutral",
                "nino34_jja": float(climate_held["nino34_jja"].iloc[0]),
                "dmi_jja": float(climate_held["dmi_jja"].iloc[0]),
            }])
            pred = predict_model_d(fit, forecast_years=[held],
                                   climate_future=climate_in, towers=towers)
            obs_panel = panel[panel["year"] == held].set_index("tower_id")
            pred_panel = pred.set_index("tower_id")

            for tgt, pcol in (("count", "count_p50"),
                              ("density", "density_p50"),
                              ("mean_ka", "mean_ka_p50"),
                              ("max_ka", "max_ka_p50")):
                obs = obs_panel[tgt].reindex(pred_panel.index)
                pj = pred_panel[pcol]
                mask = obs.notna() & pj.notna()
                if mask.sum() == 0:
                    continue
                obs_v = obs[mask].to_numpy()
                pj_v = pj[mask].to_numpy()
                row = {
                    "scheme": "LOYO",
                    "target": tgt,
                    "model": "D",
                    "year_held": int(held),
                    "half_life": float(hl) if not math.isinf(hl) else None,
                    "ridge_alpha": float(ra),
                    "MAE": _mae(obs_v, pj_v),
                    "RMSE": _rmse(obs_v, pj_v),
                    "Deviance": (_poisson_deviance(obs_v, pj_v)
                                 if tgt in ("count", "density") else np.nan),
                    # CRPS sigma matches Model C convention (build_notebook.py):
                    # per-prediction sigma = max(0.5, sqrt(pred)) — Poisson-like
                    # dispersion. Earlier versions used fold-constant sd which
                    # broke cross-model comparability of the CRPS column.
                    "CRPS": _gaussian_crps(obs_v, pj_v,
                                            sd=np.maximum(0.5,
                                                           np.sqrt(np.maximum(pj_v, 0.0)))),
                }
                rows.append(row)
        except Exception as e:
            rows.append({
                "scheme": "LOYO", "target": "count", "model": "D",
                "year_held": int(held),
                "half_life": float(hl) if not math.isinf(hl) else None,
                "ridge_alpha": float(ra),
                "MAE": np.nan, "RMSE": np.nan, "Deviance": np.nan, "CRPS": np.nan,
                "error": str(e)[:200],
            })

    return pd.DataFrame(rows)


def cv_expanding_d(
    panel: pd.DataFrame,
    line_year: pd.DataFrame,
    towers: pd.DataFrame,
    *,
    elev: pd.Series | None = None,
    dist_coast: pd.Series | None = None,
    min_train: int = 3,
) -> pd.DataFrame:
    """Expanding-window walk-forward CV for Model D.

    Predict year t* using years 2019..t*-1 (≥ min_train years), tuned once per
    fold via inner LOYO.
    """
    years = sorted(line_year["year"].unique().tolist())
    rows = []
    for i in range(min_train, len(years)):
        train_y = years[:i]
        held = years[i]
        p_tr = panel[panel["year"].isin(train_y)]
        l_tr = line_year[line_year["year"].isin(train_y)]

        tuned = tune_hyperparameters(p_tr, l_tr, towers,
                                      elev=elev, dist_coast=dist_coast)
        hl = tuned["best_half_life"]
        ra = tuned["best_ridge_alpha"]

        try:
            fit = fit_model_d(p_tr, l_tr, towers,
                              half_life=hl, ridge_alpha=ra,
                              elev=elev, dist_coast=dist_coast)
            climate_held = line_year[line_year["year"] == held]
            climate_in = pd.DataFrame([{
                "year": held, "scenario": "Neutral",
                "nino34_jja": float(climate_held["nino34_jja"].iloc[0]),
                "dmi_jja": float(climate_held["dmi_jja"].iloc[0]),
            }])
            pred = predict_model_d(fit, forecast_years=[held],
                                   climate_future=climate_in, towers=towers)
            obs_panel = panel[panel["year"] == held].set_index("tower_id")
            pred_panel = pred.set_index("tower_id")
            for tgt, pcol in (("count", "count_p50"),
                              ("density", "density_p50"),
                              ("mean_ka", "mean_ka_p50"),
                              ("max_ka", "max_ka_p50")):
                obs = obs_panel[tgt].reindex(pred_panel.index)
                pj = pred_panel[pcol]
                mask = obs.notna() & pj.notna()
                if mask.sum() == 0:
                    continue
                obs_v = obs[mask].to_numpy()
                pj_v = pj[mask].to_numpy()
                rows.append({
                    "scheme": "Expanding",
                    "target": tgt,
                    "model": "D",
                    "year_held": int(held),
                    "half_life": float(hl) if not math.isinf(hl) else None,
                    "ridge_alpha": float(ra),
                    "MAE": _mae(obs_v, pj_v),
                    "RMSE": _rmse(obs_v, pj_v),
                    "Deviance": (_poisson_deviance(obs_v, pj_v)
                                 if tgt in ("count", "density") else np.nan),
                    # CRPS sigma matches Model C convention (build_notebook.py):
                    # per-prediction sigma = max(0.5, sqrt(pred)) — Poisson-like
                    # dispersion. Earlier versions used fold-constant sd which
                    # broke cross-model comparability of the CRPS column.
                    "CRPS": _gaussian_crps(obs_v, pj_v,
                                            sd=np.maximum(0.5,
                                                           np.sqrt(np.maximum(pj_v, 0.0)))),
                })
        except Exception as e:
            rows.append({
                "scheme": "Expanding", "target": "count", "model": "D",
                "year_held": int(held),
                "half_life": float(hl) if not math.isinf(hl) else None,
                "ridge_alpha": float(ra),
                "MAE": np.nan, "RMSE": np.nan, "Deviance": np.nan, "CRPS": np.nan,
                "error": str(e)[:200],
            })

    return pd.DataFrame(rows)
