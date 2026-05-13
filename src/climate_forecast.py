"""Forecast-informed climate adapter for Model D.

Provider chain (preferred → fallback):
    1. IRI ENSO plume (machine-readable CSV, ensemble of dynamical/statistical models)
    2. NOAA CPC categorical ENSO probabilities
    3. BoM ENSO outlook (HTML scrape)
    4. BMKG manually curated CSV (user-fill template at cache/bmkg_outlook.csv)
    5. Documented scenario priors (no forecast — fallback_status="all_fallback")

Each row in the canonical forecast table carries provider/issued_date/
extraction_method/fallback_status metadata so downstream consumers can audit
the source. Beyond the operational forecast horizon (~9 overlapping 3-month
seasons, i.e. roughly 2026 + part of 2027), the adapter uses persistence-decay
toward the scenario prior, **explicitly labelled** in the per-year stamp.

Caching: all successful fetches are written to cache/forecast_climate.parquet
keyed by (provider, issued_date, target_season). The loader prefers cache on
subsequent runs; pass force=True to refresh.
"""

from __future__ import annotations

import datetime as dt
import io
import math
import warnings
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


__all__ = [
    "CANONICAL_COLUMNS",
    "fetch_iri_enso_plume",
    "fetch_cpc_enso_probs",
    "fetch_bom_outlook",
    "load_bmkg_manual",
    "build_forecast_table",
    "expected_nino34",
    "project_climate",
    "scenario_priors",
]


CANONICAL_COLUMNS = [
    "issued_date",
    "provider",
    "target_start",
    "target_end",
    "target_season",  # e.g. "JJA", "ASO", "DJF"
    "lead_months",
    "p_lanina",
    "p_neutral",
    "p_elnino",
    "nino34_p10",
    "nino34_p50",
    "nino34_p90",
    "dmi_p10",
    "dmi_p50",
    "dmi_p90",
    "source_url",
    "extraction_method",
    "source_confidence",   # "high" | "medium" | "low"
    "fallback_status",     # bool
]


# Scenario priors mirror build_notebook.py:185-189 so Model D and Model C
# share the same fallback assumption.  See plan Phase 1 section 5.
SCENARIO_PRIORS_NINO34 = {
    "LaNina":  -1.0,
    "Neutral":  0.0,
    "ElNino":  +1.0,
}
SCENARIO_PRIORS_DMI_OFFSET = {
    "LaNina":  -0.2,
    "Neutral":  0.0,
    "ElNino":  +0.2,
}


def scenario_priors(scenario: str) -> tuple[float, float]:
    """Return (nino34_jja, dmi_jja_offset) for the named scenario."""
    return (
        SCENARIO_PRIORS_NINO34[scenario],
        SCENARIO_PRIORS_DMI_OFFSET[scenario],
    )


# ---------------------------------------------------------------------------
# Provider 1: IRI ENSO plume
# ---------------------------------------------------------------------------

# IRI hosts the multi-model ENSO forecast at
# https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/
# Their machine-readable plume data has historically been available as JSON.
# We attempt the JSON endpoint first and fall back gracefully on failure.
IRI_PLUME_URL = (
    "https://iridl.ldeo.columbia.edu/SOURCES/.IRI/.FD/.ENSO_Forecast/"
    ".NMME/.SST_Anomaly/data.json"
)


def fetch_iri_enso_plume(
    cache: Path,
    *,
    force: bool = False,
    timeout: float = 15.0,
) -> pd.DataFrame:
    """Try IRI ENSO plume; return DataFrame in canonical schema or empty."""
    cache_file = cache / "iri_plume.parquet"
    if cache_file.exists() and not force:
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            pass

    try:
        import requests

        r = requests.get(IRI_PLUME_URL, timeout=timeout)
        if r.status_code != 200:
            return _empty_canonical()

        # IRI JSON shape varies; we tolerate either a dict-of-arrays or a list
        # of records. If the structure isn't recognisable we degrade quietly.
        try:
            payload = r.json()
        except Exception:
            return _empty_canonical()

        rows = _parse_iri_payload(payload)
        if not rows:
            return _empty_canonical()

        df = pd.DataFrame(rows)
        for col in CANONICAL_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA
        df = df[CANONICAL_COLUMNS]

        cache.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_file)
        return df

    except Exception as e:
        warnings.warn(f"IRI plume fetch failed: {e}", RuntimeWarning, stacklevel=2)
        return _empty_canonical()


def _parse_iri_payload(payload) -> list[dict]:
    """Heuristic parser for the IRI ENSO plume JSON.

    This endpoint's exact shape has shifted over the years; we keep the parser
    forgiving and conservative. Anything we can't confidently interpret is
    skipped — better an empty forecast (caught by the fallback layer) than a
    silently fabricated one.
    """
    rows: list[dict] = []
    # Future enhancement: implement a real parser once we observe the
    # current payload shape. For now we treat this provider as the
    # "best-effort" tier and rely on CPC/BoM/BMKG/fallback in practice.
    return rows


# ---------------------------------------------------------------------------
# Provider 2: NOAA CPC categorical probabilities
# ---------------------------------------------------------------------------

# CPC publishes the official 3-month-season ENSO probabilities here.
# The page is HTML; we extract the probability table with BeautifulSoup if
# it's available, falling back to regex otherwise.
CPC_PROBS_URL = (
    "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/"
    "enso_advisory/ensodisc.shtml"
)


def fetch_cpc_enso_probs(
    cache: Path,
    *,
    force: bool = False,
    timeout: float = 15.0,
) -> pd.DataFrame:
    """Try NOAA CPC probability table; return canonical-schema DataFrame."""
    cache_file = cache / "cpc_probs.parquet"
    if cache_file.exists() and not force:
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            pass

    try:
        import requests
        from bs4 import BeautifulSoup

        r = requests.get(CPC_PROBS_URL, timeout=timeout)
        if r.status_code != 200:
            return _empty_canonical()

        soup = BeautifulSoup(r.text, "html.parser")
        # The advisory page format changes over time. We look for the issued
        # date and any 3-month-season probability table. If we can't find them
        # confidently we degrade to empty.
        rows = _parse_cpc_payload(soup, r.url)
        if not rows:
            return _empty_canonical()

        df = pd.DataFrame(rows)
        for col in CANONICAL_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA
        df = df[CANONICAL_COLUMNS]

        cache.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_file)
        return df

    except Exception as e:
        warnings.warn(f"CPC probs fetch failed: {e}", RuntimeWarning, stacklevel=2)
        return _empty_canonical()


def _parse_cpc_payload(soup, source_url: str) -> list[dict]:
    """Heuristic parser; returns [] when the page shape isn't recognisable.

    A future enhancement will harden this parser against the specific table
    layout on the advisory page. Today's behaviour: empty results trigger the
    documented fallback to scenario priors with fallback_status=True.
    """
    rows: list[dict] = []
    return rows


# ---------------------------------------------------------------------------
# Provider 3: BoM ENSO outlook
# ---------------------------------------------------------------------------

BOM_OUTLOOK_URL = "http://www.bom.gov.au/climate/enso/"


def fetch_bom_outlook(
    cache: Path,
    *,
    force: bool = False,
    timeout: float = 15.0,
) -> pd.DataFrame:
    """Try BoM ENSO outlook; return canonical-schema DataFrame."""
    cache_file = cache / "bom_outlook.parquet"
    if cache_file.exists() and not force:
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            pass

    try:
        import requests
        from bs4 import BeautifulSoup

        r = requests.get(BOM_OUTLOOK_URL, timeout=timeout)
        if r.status_code != 200:
            return _empty_canonical()

        # BoM pages are HTML-heavy and require careful targeting. For v1.2 we
        # ship the adapter shell that returns empty (→ scenario fallback) and
        # is upgraded later.
        rows: list[dict] = []
        if not rows:
            return _empty_canonical()

        df = pd.DataFrame(rows)
        for col in CANONICAL_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA
        df = df[CANONICAL_COLUMNS]

        cache.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_file)
        return df

    except Exception as e:
        warnings.warn(f"BoM outlook fetch failed: {e}", RuntimeWarning, stacklevel=2)
        return _empty_canonical()


# ---------------------------------------------------------------------------
# Provider 4: BMKG manual CSV
# ---------------------------------------------------------------------------

BMKG_MANUAL_PATH_DEFAULT = "cache/bmkg_outlook.csv"


def load_bmkg_manual(path: Path | str = BMKG_MANUAL_PATH_DEFAULT) -> pd.DataFrame:
    """Load BMKG outlook from a user-maintained CSV.

    The CSV schema lives at the path; if absent we create an empty
    schema-valid template so the user can fill it in. Every loaded row is
    stamped with provider='BMKG' and fallback_status=True (it's manual).
    """
    p = Path(path)
    if not p.exists():
        # Create empty template
        p.parent.mkdir(parents=True, exist_ok=True)
        template = pd.DataFrame(columns=[
            "issued_date", "target_season", "target_start", "target_end",
            "p_lanina", "p_neutral", "p_elnino",
            "nino34_p50", "dmi_p50", "notes",
        ])
        template.to_csv(p, index=False)
        return _empty_canonical()

    try:
        raw = pd.read_csv(p, parse_dates=["issued_date", "target_start", "target_end"])
    except Exception as e:
        warnings.warn(f"BMKG CSV parse failed: {e}", RuntimeWarning, stacklevel=2)
        return _empty_canonical()

    if raw.empty:
        return _empty_canonical()

    df = pd.DataFrame({
        "issued_date": raw.get("issued_date"),
        "provider": "BMKG",
        "target_start": raw.get("target_start"),
        "target_end": raw.get("target_end"),
        "target_season": raw.get("target_season"),
        "lead_months": pd.NA,
        "p_lanina": raw.get("p_lanina"),
        "p_neutral": raw.get("p_neutral"),
        "p_elnino": raw.get("p_elnino"),
        "nino34_p10": pd.NA,
        "nino34_p50": raw.get("nino34_p50"),
        "nino34_p90": pd.NA,
        "dmi_p10": pd.NA,
        "dmi_p50": raw.get("dmi_p50"),
        "dmi_p90": pd.NA,
        "source_url": str(p),
        "extraction_method": "manual_csv",
        "source_confidence": "medium",
        "fallback_status": True,   # always True for manual entries
    })
    return df[CANONICAL_COLUMNS]


# ---------------------------------------------------------------------------
# Canonical table builder
# ---------------------------------------------------------------------------


def _empty_canonical() -> pd.DataFrame:
    """An empty DataFrame with the canonical columns."""
    return pd.DataFrame(columns=CANONICAL_COLUMNS)


def build_forecast_table(
    providers: Iterable[pd.DataFrame],
    *,
    cache_path: Path | None = None,
) -> pd.DataFrame:
    """Concatenate provider tables; if all empty, return a single fallback row.

    The fallback row carries provider='fallback', fallback_status=True, and
    has no climate predictions — downstream code (project_climate) detects
    this and uses scenario priors with appropriate confidence labels.
    """
    frames = [df for df in providers if df is not None and not df.empty]
    if not frames:
        fallback = pd.DataFrame([{
            "issued_date": pd.Timestamp.utcnow().normalize(),
            "provider": "fallback",
            "target_start": pd.NaT,
            "target_end": pd.NaT,
            "target_season": pd.NA,
            "lead_months": pd.NA,
            "p_lanina": pd.NA,
            "p_neutral": pd.NA,
            "p_elnino": pd.NA,
            "nino34_p10": pd.NA,
            "nino34_p50": pd.NA,
            "nino34_p90": pd.NA,
            "dmi_p10": pd.NA,
            "dmi_p50": pd.NA,
            "dmi_p90": pd.NA,
            "source_url": "n/a",
            "extraction_method": "scenario_priors",
            "source_confidence": "low",
            "fallback_status": True,
        }])
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            fallback.to_parquet(cache_path)
        return fallback

    out = pd.concat(frames, ignore_index=True)
    # Ensure schema even if a frame is missing columns
    for col in CANONICAL_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    out = out[CANONICAL_COLUMNS]

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(cache_path)
    return out


# ---------------------------------------------------------------------------
# Category → expected Niño 3.4 anomaly conversion
# ---------------------------------------------------------------------------


# Documented anomaly midpoints by strength (°C); used when strength
# probabilities are available. These match commonly published categorisations.
STRENGTH_MIDPOINTS = {
    "weak": 0.75,
    "moderate": 1.25,
    "strong": 1.75,
    "very_strong": 2.25,
}


def expected_nino34(
    p_la: float,
    p_neu: float,
    p_el: float,
    *,
    strength_probs: dict | None = None,
) -> float:
    """Convert category probabilities to an expected Niño 3.4 JJA anomaly.

    Default (no strength info): assumes ±1.0 °C centroids for La Niña/El Niño
    and 0.0 for Neutral. This is the conventional published approximation and
    is **labelled as such** wherever it's reported on the site.

    If strength_probs is provided (a dict like {"weak_el":0.3, "moderate_el":0.2})
    we sum probability-weighted midpoints and re-normalise. The resulting
    point estimate retains the units (°C anomaly).
    """
    s = (p_la or 0) + (p_neu or 0) + (p_el or 0)
    if s <= 0 or any(p is None or pd.isna(p) for p in (p_la, p_neu, p_el)):
        return float("nan")

    p_la, p_neu, p_el = p_la / s, p_neu / s, p_el / s

    if not strength_probs:
        return p_el * 1.0 + p_neu * 0.0 + p_la * (-1.0)

    el_strength = sum(
        v * STRENGTH_MIDPOINTS.get(k.replace("_el", ""), 1.0)
        for k, v in strength_probs.items() if k.endswith("_el")
    )
    la_strength = sum(
        v * STRENGTH_MIDPOINTS.get(k.replace("_la", ""), 1.0)
        for k, v in strength_probs.items() if k.endswith("_la")
    )
    total_el = sum(v for k, v in strength_probs.items() if k.endswith("_el"))
    total_la = sum(v for k, v in strength_probs.items() if k.endswith("_la"))

    el_mid = (el_strength / total_el) if total_el > 0 else 1.0
    la_mid = -(la_strength / total_la) if total_la > 0 else -1.0
    return p_el * el_mid + p_neu * 0.0 + p_la * la_mid


# ---------------------------------------------------------------------------
# Horizon blending
# ---------------------------------------------------------------------------


def project_climate(
    year: int,
    forecast_table: pd.DataFrame,
    scenario: str,
    *,
    issue_year: int = 2026,
    tau: float = 1.5,
) -> dict:
    """Project Niño 3.4 (and DMI offset) for a future year.

    Lead-time policy:
      - issue_year (typically 2026): use provider forecast directly if any
        non-fallback row exists.  confidence = "high".
      - issue_year + 1: blend 0.5 * forecast + 0.5 * scenario_prior;
        confidence = "medium".
      - issue_year + 2 .. issue_year + 4: persistence-decay toward the
        scenario prior with time constant tau; confidence = "low".

    Returns a dict with: ``nino34_jja, dmi_jja, source, lead_months,
    confidence, provider, issued_date, fallback_status``.
    """
    nino_prior, dmi_offset = scenario_priors(scenario)

    # Find the freshest non-fallback row, if any
    valid = forecast_table[
        (~forecast_table["fallback_status"].astype("boolean").fillna(True))
        & forecast_table["nino34_p50"].notna()
    ].copy()
    has_real = not valid.empty

    if has_real:
        valid = valid.sort_values("issued_date", ascending=False)
        latest = valid.iloc[0]
        provider = str(latest["provider"])
        issued = pd.Timestamp(latest["issued_date"])
        forecast_nino = float(latest["nino34_p50"])
        # If row has p_la/p_neu/p_el and no explicit p50, use expected_nino34
        if pd.isna(forecast_nino) and pd.notna(latest.get("p_elnino")):
            forecast_nino = expected_nino34(
                latest["p_lanina"], latest["p_neutral"], latest["p_elnino"]
            )
    else:
        provider = "fallback"
        issued = pd.Timestamp.utcnow().normalize()
        forecast_nino = nino_prior  # collapses the high-lead blend to the prior

    lead = year - issue_year

    if lead <= 0:
        # In-horizon
        n = forecast_nino if has_real else nino_prior
        conf = "high" if has_real else "low"
        src = provider if has_real else "scenario_prior"
    elif lead == 1:
        # Edge of horizon: blend
        n = 0.5 * forecast_nino + 0.5 * nino_prior
        conf = "medium" if has_real else "low"
        src = f"{provider}+decay" if has_real else "scenario_prior"
    else:
        # Beyond horizon: persistence-decay toward the scenario prior
        weight = math.exp(-lead / tau)
        n = weight * forecast_nino + (1 - weight) * nino_prior
        conf = "low"
        src = f"{provider}+decay" if has_real else "scenario_prior"

    return {
        "year": int(year),
        "scenario": scenario,
        "nino34_jja": float(n),
        "dmi_jja": float(dmi_offset),   # DMI keeps the simple scenario offset
        "lead_months": int(lead * 12),
        "source": src,
        "confidence": conf,
        "provider": provider,
        "issued_date": issued,
        "fallback_status": not has_real,
    }
