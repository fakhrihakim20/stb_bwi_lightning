"""Model D — forecast-informed, recency-weighted, spatially-aware extension.

Stage 1 (line-level annual count):
    Recency-weighted Negative Binomial GLM using var_weights, AICc with
    effective sample size, candidate predictors include nino34_jja, dmi_jja,
    year_idx.

Stage 2 (per-tower share):
    Weighted raw share s_i = Σ_t w_t y_{i,t} / Σ_t w_t N_t, James-Stein
    shrinkage toward the global mean, then ridge-regression spatial
    correction on (tower_order, elevation, distance-to-coast). Re-normalise.

kA (mean/max):
    Recency-weighted OLS on nino34_jja and dmi_jja; AICc selection over
    candidate predictor subsets.

Honesty safeguard:
    If the selected half_life is ∞ AND the AICc-selected count formula is
    intercept-only AND the selected kA formula is intercept-only, Model D
    is numerically equivalent to a JS-shrunk climatology. We detect this and
    stamp the output with notes="reverted_to_C_no_recency_skill" so the
    website banner can warn the user.

This module imports nothing from build_notebook.py — it's standalone, which
makes unit testing easy and keeps Model C truly untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd

try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
except ImportError:  # pragma: no cover
    sm = None
    smf = None

try:
    from sklearn.linear_model import Ridge
except ImportError:  # pragma: no cover
    Ridge = None

from .recency import recency_weights, effective_n, aicc_weighted


__all__ = [
    "ModelDFit",
    "fit_model_d",
    "predict_model_d",
    "model_d_bootstrap_one",
]


CANDIDATE_FORMULAS_COUNT = {
    "D0": "count ~ 1",
    "D1": "count ~ nino34_jja",
    "D2": "count ~ nino34_jja + dmi_jja",
    "D3": "count ~ nino34_jja + year_idx",
}
CANDIDATE_FORMULAS_KA = [
    "{tgt} ~ 1",
    "{tgt} ~ nino34_jja",
    "{tgt} ~ dmi_jja",
    "{tgt} ~ nino34_jja + dmi_jja",
]


@dataclass
class ModelDFit:
    """Container for the fitted Model D."""

    half_life: float
    ridge_alpha: float
    n_eff: float

    count_formula: str
    count_result: object             # statsmodels GLMResults
    count_alpha: float               # NB dispersion

    mean_ka_formula: str
    mean_ka_result: object
    max_ka_formula: str
    max_ka_result: object

    # Stage 2 outputs
    shares_count: pd.Series          # index = tower_id, sums to 1
    shares_density: pd.Series
    shares_kamean_offset: pd.Series  # per-tower kA offset (additive)
    shares_kamax_offset: pd.Series

    # Conversion factor from line count to line density (empirically fixed by
    # collection geometry — Model C uses ~880 km² line collection area).
    density_per_count: float = 1.0

    ridge_diagnostics: dict = field(default_factory=dict)
    notes: str = ""

    @property
    def is_reverted_to_c(self) -> bool:
        """True when Model D collapsed to a no-recency climatology."""
        return (
            (self.half_life == float("inf"))
            and (self.count_formula == CANDIDATE_FORMULAS_COUNT["D0"])
            and (self.mean_ka_formula.endswith("~ 1"))
            and (self.max_ka_formula.endswith("~ 1"))
        )


def fit_model_d(
    panel: pd.DataFrame,
    line_year: pd.DataFrame,
    towers: pd.DataFrame,
    *,
    half_life: float = 3.0,
    ridge_alpha: float = 10.0,
    elev: pd.Series | None = None,
    dist_coast: pd.Series | None = None,
) -> ModelDFit:
    """Fit Model D on training panels.

    Parameters
    ----------
    panel : DataFrame
        Per-tower per-year exposure with columns:
        ``tower_id, year, count, density, mean_ka, max_ka`` (plus
        ``nino34_jja, dmi_jja`` merged in for the climate stage).
    line_year : DataFrame
        Line-aggregate annual totals with columns:
        ``year, count, mean_ka, max_ka, nino34_jja, dmi_jja``.
    towers : DataFrame
        Tower metadata with columns ``tower_id`` (and indices for elev/dist).
    half_life : float
        Recency half-life in years.  ``math.inf`` disables recency weighting.
    ridge_alpha : float
        Ridge penalty for the spatial correction.
    elev, dist_coast : Series, optional
        Per-tower elevation / distance-to-coast (indexed by tower_id).
        If omitted the spatial correction is skipped (logged in
        ``ridge_diagnostics``).
    """
    if sm is None or smf is None:
        raise RuntimeError("statsmodels is required for Model D")

    years = sorted(line_year["year"].unique().tolist())
    w = recency_weights(years, half_life)
    n_eff = effective_n(w)

    line_year = line_year.copy()
    line_year["year_idx"] = line_year["year"] - line_year["year"].min()
    line_year["_w"] = line_year["year"].map(w).astype(float)

    # ---------------- Stage 1: count NB GLM ----------------
    best_count = _select_nb_glm(
        line_year, target="count", weights_col="_w", n_eff=n_eff
    )

    # ---------------- kA models ----------------
    best_mean_ka = _select_gaussian(
        line_year, target="mean_ka", weights_col="_w", n_eff=n_eff
    )
    best_max_ka = _select_gaussian(
        line_year, target="max_ka", weights_col="_w", n_eff=n_eff
    )

    # ---------------- Stage 2: tower share ----------------
    panel = panel.copy()
    panel["_w"] = panel["year"].map(w).astype(float)
    line_count_by_year = panel.groupby("year")["count"].sum()
    line_density_by_year = panel.groupby("year")["density"].sum()

    shares_count = _weighted_js_share(
        panel, value_col="count", weights_col="_w",
        line_total_by_year=line_count_by_year, n_eff=n_eff,
    )
    shares_density = _weighted_js_share(
        panel, value_col="density", weights_col="_w",
        line_total_by_year=line_density_by_year, n_eff=n_eff,
    )

    ridge_diag: dict = {}
    if elev is not None and dist_coast is not None and Ridge is not None:
        shares_count, diag_c = _ridge_spatial_correction(
            shares_count, elev, dist_coast, alpha=ridge_alpha
        )
        shares_density, diag_d = _ridge_spatial_correction(
            shares_density, elev, dist_coast, alpha=ridge_alpha
        )
        ridge_diag = {"count": diag_c, "density": diag_d}
    else:
        ridge_diag = {"note": "spatial correction skipped (missing covariates)"}

    # Per-tower kA offsets (weighted line-relative residuals)
    panel_join = panel.merge(line_year[["year", "mean_ka", "max_ka"]]
                              .rename(columns={"mean_ka": "line_mean_ka",
                                               "max_ka": "line_max_ka"}),
                              on="year", how="left")
    panel_join["res_mean_ka"] = panel_join["mean_ka"] - panel_join["line_mean_ka"]
    panel_join["res_max_ka"] = panel_join["max_ka"] - panel_join["line_max_ka"]

    shares_kamean_offset = _weighted_mean_by(panel_join, "res_mean_ka", "_w", "tower_id")
    shares_kamax_offset  = _weighted_mean_by(panel_join, "res_max_ka",  "_w", "tower_id")

    # Empirical density-per-count ratio at the PER-TOWER level. The per-tower
    # collection area in the Vaisala/IEEE convention is geometry-fixed, so
    # ratio = density_i / count_i is nearly constant across (tower, year).
    # We compute the weighted mean of per-tower per-year ratios.
    if "density" in panel.columns and "count" in panel.columns:
        ratio_series = (panel["density"] / panel["count"].replace(0, np.nan)).dropna()
        if len(ratio_series):
            w_series = panel.loc[ratio_series.index, "_w"].fillna(1.0)
            density_per_count = float(
                np.average(ratio_series.to_numpy(), weights=w_series.to_numpy())
            )
        else:
            density_per_count = 1.0
    else:
        density_per_count = 1.0

    notes = ""
    fit = ModelDFit(
        half_life=float(half_life),
        ridge_alpha=float(ridge_alpha),
        n_eff=float(n_eff),
        count_formula=best_count["formula"],
        count_result=best_count["result"],
        count_alpha=best_count["alpha"],
        mean_ka_formula=best_mean_ka["formula"],
        mean_ka_result=best_mean_ka["result"],
        max_ka_formula=best_max_ka["formula"],
        max_ka_result=best_max_ka["result"],
        shares_count=shares_count,
        shares_density=shares_density,
        shares_kamean_offset=shares_kamean_offset,
        shares_kamax_offset=shares_kamax_offset,
        density_per_count=density_per_count,
        ridge_diagnostics=ridge_diag,
        notes=notes,
    )

    if fit.is_reverted_to_c:
        fit.notes = "reverted_to_C_no_recency_skill"

    return fit


def _select_nb_glm(line_year: pd.DataFrame, *, target: str,
                   weights_col: str, n_eff: float) -> dict:
    """AICc-select an NB GLM among the candidate formulas."""
    best = None
    for tag, formula in CANDIDATE_FORMULAS_COUNT.items():
        f = formula.replace("count", target)
        try:
            # Estimate alpha from a Poisson fit residual variance
            poiss = smf.glm(f, data=line_year,
                            family=sm.families.Poisson()).fit()
            mu = poiss.fittedvalues
            resid_var = ((line_year[target] - mu) ** 2 / mu).sum() / max(1, len(line_year) - poiss.df_model)
            alpha = max(0.01, float(resid_var - 1.0) / max(mu.mean(), 1e-6))

            res = smf.glm(f, data=line_year,
                          family=sm.families.NegativeBinomial(alpha=alpha),
                          var_weights=line_year[weights_col]).fit()
            k = int(res.df_model) + 1
            aicc = aicc_weighted(float(res.llf), k, n_eff)
            cand = {"tag": tag, "formula": f, "result": res, "alpha": alpha, "aicc": aicc}
            if best is None or cand["aicc"] < best["aicc"]:
                best = cand
        except Exception:
            continue
    if best is None:
        # Last-resort: intercept-only Poisson, alpha=1.0
        f = f"{target} ~ 1"
        res = smf.glm(f, data=line_year, family=sm.families.Poisson()).fit()
        best = {"tag": "fallback", "formula": f, "result": res, "alpha": 1.0,
                "aicc": float("inf")}
    return best


def _select_gaussian(line_year: pd.DataFrame, *, target: str,
                     weights_col: str, n_eff: float) -> dict:
    """AICc-select a weighted OLS for kA targets."""
    best = None
    for tmpl in CANDIDATE_FORMULAS_KA:
        f = tmpl.format(tgt=target)
        try:
            res = smf.wls(f, data=line_year,
                          weights=line_year[weights_col]).fit()
            k = int(res.df_model) + 1
            aicc = aicc_weighted(float(res.llf), k, n_eff)
            cand = {"formula": f, "result": res, "aicc": aicc}
            if best is None or cand["aicc"] < best["aicc"]:
                best = cand
        except Exception:
            continue
    if best is None:
        f = f"{target} ~ 1"
        res = smf.ols(f, data=line_year).fit()
        best = {"formula": f, "result": res, "aicc": float("inf")}
    return best


def _weighted_js_share(
    panel: pd.DataFrame,
    *,
    value_col: str,
    weights_col: str,
    line_total_by_year: pd.Series,
    n_eff: float,
) -> pd.Series:
    """Weighted raw share + James-Stein shrinkage toward the global mean.

    Raw share per tower:
        s_i = Σ_t w_t · y_{i,t} / Σ_t w_t · N_t

    Then shrink toward the grand mean using a JS-style coefficient with
    effective sample size:
        a_i = σ²_between / (σ²_between + σ²_within,i / n_eff)
        s_i_shrunk = a_i * s_i_raw + (1 - a_i) * s_global
    Finally re-normalise so Σ_i s_i = 1.
    """
    # Numerator: sum_t w_t * y_it
    panel = panel.copy()
    panel["_wy"] = panel[weights_col] * panel[value_col]
    num = panel.groupby("tower_id")["_wy"].sum()

    # Denominator: sum_t w_t * N_t — independent of tower
    panel["_wN"] = panel[weights_col] * panel["year"].map(line_total_by_year).astype(float)
    denom_per_tower = panel.groupby("tower_id")["_wN"].sum()

    raw = num / denom_per_tower
    raw = raw.replace([np.inf, -np.inf], np.nan).fillna(raw.mean())

    s_global = float(raw.mean())
    # Between-tower variance (target signal); within-tower variance (noise)
    # Within-tower: variance of weighted year-level share for each tower
    # Bypass per-tower noise estimate when n_eff small — collapse to a single
    # shrinkage factor based on the between/within ratio in the panel.
    sigma_between = float(raw.var(ddof=0))
    # Aggregate within-tower variance using weighted yearly share residuals
    panel["_share_t"] = (
        panel[value_col] / panel["year"].map(line_total_by_year).replace(0, np.nan)
    )
    panel["_share_t"] = panel["_share_t"].fillna(0.0)
    within = panel.groupby("tower_id").apply(
        lambda g: np.average((g["_share_t"] - raw.get(g.name, s_global)) ** 2,
                              weights=g[weights_col])
    )
    sigma_within = float(within.mean())

    if sigma_between <= 0:
        a = 0.0  # all global; raw shares are identical
    else:
        a = sigma_between / (sigma_between + sigma_within / max(n_eff, 1.0))
    shrunk = a * raw + (1 - a) * s_global
    # Re-normalise to sum to 1 (raw is already share-of-line, but
    # shrinkage perturbs the sum slightly)
    shrunk = shrunk / shrunk.sum()
    shrunk.name = "share"
    shrunk.index.name = "tower_id"
    return shrunk


def _ridge_spatial_correction(
    shares: pd.Series,
    elev: pd.Series,
    dist_coast: pd.Series,
    *,
    alpha: float = 10.0,
) -> tuple[pd.Series, dict]:
    """Ridge correction of log(share) on (tower_order, elev_z, dist_coast_z).

    Fits a low-degree ridge regression on the JS-shrunk shares (stabilised
    targets), then re-normalises the corrected shares to sum to 1.

    Returns (corrected_shares, diagnostics_dict).
    """
    if Ridge is None:
        return shares, {"note": "sklearn not available"}

    ids = shares.index.to_numpy()
    order = np.arange(len(ids), dtype=float)
    order_n = (order - order.mean()) / max(order.std(), 1e-6)
    elev_v = elev.reindex(ids).astype(float).fillna(elev.mean()).to_numpy()
    elev_z = (elev_v - elev_v.mean()) / max(elev_v.std(), 1e-6)
    dist_v = dist_coast.reindex(ids).astype(float).fillna(dist_coast.mean()).to_numpy()
    dist_z = (dist_v - dist_v.mean()) / max(dist_v.std(), 1e-6)

    X = np.column_stack([order_n, elev_z, dist_z])
    y = np.log(np.clip(shares.to_numpy(), 1e-12, None))

    model = Ridge(alpha=alpha, fit_intercept=True)
    model.fit(X, y)
    y_hat = model.predict(X)
    # Damp the correction to avoid runaway moves on a tiny sample
    # (cap |Δlog-share| at the 95th percentile of inter-tower log-share spread)
    delta = y_hat - y_hat.mean()
    cap = float(np.quantile(np.abs(delta), 0.95))
    delta = np.clip(delta, -cap, cap)
    corrected = np.exp(y + delta)
    corrected = corrected / corrected.sum()

    out = pd.Series(corrected, index=shares.index, name="share")
    diag = {
        "alpha": float(alpha),
        "coef": dict(zip(["tower_order", "elev", "dist_coast"], model.coef_.tolist())),
        "intercept": float(model.intercept_),
        "delta_log_share_p95": cap,
        "n_capped": int(np.sum(np.abs(y_hat - y_hat.mean()) > cap)),
    }
    return out, diag


def _weighted_mean_by(df: pd.DataFrame, value_col: str, weight_col: str,
                     group_col: str) -> pd.Series:
    """Weighted mean of value_col within each group."""
    def _agg(g):
        w = g[weight_col]
        return float(np.average(g[value_col], weights=w))
    return df.groupby(group_col).apply(_agg).rename(value_col)


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------


def predict_model_d(
    fit: ModelDFit,
    *,
    forecast_years: Iterable[int],
    climate_future: pd.DataFrame,
    towers: pd.DataFrame,
) -> pd.DataFrame:
    """Generate per-tower predictions for forecast_years.

    Parameters
    ----------
    fit : ModelDFit
    forecast_years : iterable of int
    climate_future : DataFrame
        One row per (year, scenario) with columns
        ``year, scenario, nino34_jja, dmi_jja``.
    towers : DataFrame
        Tower metadata; must have ``tower_id``.

    Returns
    -------
    DataFrame in long format with columns:
        tower_id, year, scenario, count_p50, density_p50,
        mean_ka_p50, max_ka_p50, model='D', notes
    """
    out_rows = []
    for _, climate in climate_future.iterrows():
        year = int(climate["year"])
        scenario = str(climate["scenario"])
        # Build a 1-row design with year_idx (relative to training)
        design = pd.DataFrame([{
            "nino34_jja": float(climate["nino34_jja"]),
            "dmi_jja": float(climate["dmi_jja"]),
            "year_idx": year - 2019,
        }])

        line_count = float(fit.count_result.predict(design).iloc[0])
        line_mean_ka = float(fit.mean_ka_result.predict(design).iloc[0])
        line_max_ka  = float(fit.max_ka_result.predict(design).iloc[0])

        for tid, s_c in fit.shares_count.items():
            mk_off = fit.shares_kamean_offset.get(tid, 0.0)
            xk_off = fit.shares_kamax_offset.get(tid, 0.0)
            # Tower count = line_count × share. Density is derived from count
            # via the per-tower geometric ratio (Vaisala 3.125 km² per tower
            # → ratio ≈ 0.32). Since this ratio is empirically constant across
            # (tower, year), density_p50 = count_p50 × density_per_count.
            tower_count = line_count * s_c
            out_rows.append({
                "tower_id": int(tid),
                "year": year,
                "scenario": scenario,
                "count_p50":   tower_count,
                "density_p50": tower_count * fit.density_per_count,
                "mean_ka_p50": line_mean_ka + float(mk_off),
                "max_ka_p50":  line_max_ka  + float(xk_off),
                "model": "D",
                "notes": fit.notes,
                "provider": climate.get("provider", "fallback"),
                "issued_date": climate.get("issued_date"),
                "confidence":  climate.get("confidence", "low"),
                "fallback_status": bool(climate.get("fallback_status", True)),
            })

    out = pd.DataFrame(out_rows)
    # Use the panel-level density share as the density forecast; the formula
    # above keeps it numerically clean.
    return out


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


def model_d_bootstrap_one(
    panel: pd.DataFrame,
    line_year: pd.DataFrame,
    towers: pd.DataFrame,
    climate_future: pd.DataFrame,
    *,
    half_life: float,
    ridge_alpha: float,
    elev: pd.Series | None,
    dist_coast: pd.Series | None,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Single bootstrap replicate for Model D.

    Resamples years with replacement using recency-weighted probabilities,
    refits Model D, and returns the per-tower predictions plus NB process
    noise drawn from the fitted predictive distribution.
    """
    years = np.array(sorted(line_year["year"].unique().tolist()))
    w = recency_weights(years.tolist(), half_life).reindex(years).to_numpy()
    p = w / w.sum()
    pick = rng.choice(years, size=len(years), replace=True, p=p)

    line_boot = pd.concat([line_year[line_year["year"] == y] for y in pick],
                          ignore_index=True)
    panel_boot = pd.concat([panel[panel["year"] == y] for y in pick],
                           ignore_index=True)
    # Reassign synthetic years 2019..2019+n-1 so year_idx stays well-defined
    new_years = np.arange(2019, 2019 + len(pick))
    year_map = dict(zip(pick, new_years))
    line_boot["year"] = line_boot["year"].map(year_map)
    panel_boot["year"] = panel_boot["year"].map(year_map)

    fit_b = fit_model_d(
        panel_boot, line_boot, towers,
        half_life=half_life, ridge_alpha=ridge_alpha,
        elev=elev, dist_coast=dist_coast,
    )
    pred = predict_model_d(fit_b,
                           forecast_years=climate_future["year"].unique().tolist(),
                           climate_future=climate_future,
                           towers=towers)

    # NB process noise on count
    alpha = max(float(fit_b.count_alpha), 1e-3)
    mu = pred["count_p50"].clip(lower=0.0).to_numpy()
    var = mu + alpha * mu * mu
    # Numpy's negative_binomial is parameterised by (n, p): mean = n*(1-p)/p,
    # var = n*(1-p)/p^2. Solve for (n, p):
    p_nb = np.clip(mu / np.maximum(var, 1e-6), 1e-6, 1 - 1e-6)
    n_nb = np.clip(mu * p_nb / np.maximum(1 - p_nb, 1e-6), 1e-3, None)
    pred["count_sample"] = rng.negative_binomial(n_nb, p_nb).astype(float)
    pred["density_sample"] = pred["count_sample"] * fit_b.density_per_count
    pred["mean_ka_sample"] = pred["mean_ka_p50"] + rng.normal(0, 3.0, len(pred))
    pred["max_ka_sample"]  = pred["max_ka_p50"]  + rng.normal(0, 5.0, len(pred))
    return pred
