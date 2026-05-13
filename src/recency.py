"""Recency-weighting utilities for Model D.

The user's brief explicitly says the "deep-learning-like" requirement means
exponential decay / temporal attention, NOT a neural network. We implement
this as classical sample weighting:

    w_t = 0.5 ** ((T_max - t) / half_life)

For statsmodels GLMs we plug these into ``var_weights`` (not ``freq_weights`` —
freq_weights inflate degrees of freedom and break AICc). For ridge regressions
we multiply the design matrix and response by sqrt(w) (Kahnemen weighted
least squares trick).

AICc/BIC with weighted data uses the **effective sample size** (Kish):

    n_eff = (sum w)**2 / sum(w**2)

A uniform weight vector recovers n_eff == n. Shorter half_life → smaller
n_eff, larger model-complexity penalty — which is the correct Bayesian
behaviour when recent observations are given more influence.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd


__all__ = [
    "recency_weights",
    "effective_n",
    "aicc_weighted",
]


def recency_weights(
    years: Iterable[int],
    half_life: float | None,
    *,
    anchor_year: int | None = None,
) -> pd.Series:
    """Return exponential half-life weights, indexed by year, summing to len(years).

    Parameters
    ----------
    years : iterable of int
        The training years (e.g. range(2019, 2026)).
    half_life : float or None
        Half-life in years.  ``None`` or ``math.inf`` → uniform weights (the
        special "no recency weighting" case which makes Model D collapse to a
        Model-C-like weighting).
    anchor_year : int, optional
        The year that receives w = 1.0 before normalisation. Default: max(years).

    Returns
    -------
    pd.Series indexed by year, summing to len(years).

    Examples
    --------
    >>> w = recency_weights([2019, 2020, 2021, 2022, 2023, 2024, 2025], half_life=3)
    >>> round(w.sum(), 6)
    7.0
    >>> w[2025] > w[2019]
    True
    >>> w_uniform = recency_weights(range(2019, 2026), half_life=None)
    >>> round(w_uniform.std(), 6)
    0.0
    """
    yrs = pd.Index(sorted(set(int(y) for y in years)), name="year")
    if anchor_year is None:
        anchor_year = int(yrs.max())

    if half_life is None or math.isinf(half_life) or half_life <= 0:
        raw = pd.Series(np.ones(len(yrs)), index=yrs)
    else:
        delta = anchor_year - yrs.to_numpy()
        raw = pd.Series(0.5 ** (delta / half_life), index=yrs)

    # Normalise so the weights sum to n (preserves "effective row count" in
    # AICc when half_life=inf, matching the Model C semantics exactly).
    w = raw * (len(yrs) / raw.sum())
    w.name = "weight"
    return w


def effective_n(weights: pd.Series | np.ndarray) -> float:
    """Kish effective sample size: ``(sum w)**2 / sum(w**2)``.

    Equals n when weights are uniform; equals 1 when only one weight is non-zero.
    """
    w = np.asarray(weights, dtype=float)
    s = w.sum()
    if s <= 0:
        return 0.0
    return float(s * s / np.sum(w * w))


def aicc_weighted(loglik: float, k: int, n_eff: float) -> float:
    """AICc with effective sample size.

    AICc = -2*loglik + 2*k + 2*k*(k+1)/(n_eff - k - 1)

    Falls back to BIC-like penalty if n_eff - k - 1 <= 0 (saturated model).
    """
    base = -2.0 * loglik + 2.0 * k
    denom = n_eff - k - 1.0
    if denom <= 0:
        # Saturated model: use BIC-style penalty as documented fallback
        return base + k * math.log(max(n_eff, 1.0))
    return base + 2.0 * k * (k + 1.0) / denom
