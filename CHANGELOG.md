# Changelog

All notable changes to the Lightning GFD Forecast project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.2.0] — 2026-05-14

### Added
- **Model D — forecast-informed, recency-weighted, spatially-aware extension.**
  Model D lives in a new standalone `src/` package and runs via
  `run_model_d.py`. It coexists with Model C (Model C outputs are
  byte-identical to v1.0; rows in `forecast_2026_2030.parquet` are tagged
  with `model="C"` vs `model="D"`).
  - **Recency weighting**: exponential half-life weights
    `w_t = 0.5^((T_max−t)/half_life)`, half-life tuned via **nested LOYO**
    cross-validation over `{2, 3, 5, ∞}` × ridge α `{1, 10, 100}`.
    Effective sample size (Kish) drives AICc.
  - **Forecast-informed climate**: provider chain IRI → NOAA CPC →
    BoM → BMKG manual CSV → scenario prior. Canonical forecast table at
    `cache/forecast_climate.parquet`. Every output row stamped with
    `provider, issued_date, source_confidence, fallback_status`.
  - **Forecast-horizon blending**: 2026 = direct provider; 2027 =
    50/50 blend; 2028–2030 = persistence-decay toward prior with τ=1.5.
  - **Spatial ridge correction** on tower order, elevation, distance-to-coast
    (post JS-shrinkage targets; α tuned in CV; |Δlog-share| capped at p95
    to prevent runaway moves at n=7).
  - **Honesty safeguard**: if CV selects `half_life=∞` and all formulas
    collapse to intercept-only, Model D auto-flags
    `notes='reverted_to_C_no_recency_skill'` and the website displays a
    banner. (On the v1.2 sample, half_life=3 won — recency added skill.)
- **`src/` Python package** (5 modules): `recency`, `climate_forecast`,
  `models_d`, `cv_d`, `__init__`.
- **New outputs**: `outputs/forecast_climate_stamps.csv` (audit trail per
  year × scenario), `outputs/model_d_forecast.parquet` (D-only summary),
  `outputs/model_d_selection.csv` (hyperparameter winners per fold).
- **New website section 06 — Model C vs Model D**: comparison table,
  A/C/D skill tiles (RMSE / MAE / CRPS), line-level C-vs-D ribbon
  overlay (Figure 4), top-20 paired bars + Jaccard overlap (Figure 5),
  per-tower Δ scatter vs elevation (Figure 6).
- **Model toggle** above the existing scenario tabs in section 05
  (Figure 3) — Model C / Model D switch re-renders the per-tower profile
  while preserving the scenario tab and per-trace legend visibility.
- **CSS variables** `--model-c-color` (warm bronze), `--model-d-color`
  (ocean blue) — kept harmonious with the Editorial Luxury palette.

### Known limitations (Model D specific, in addition to v1.0 caveats)
- Model D's historical CV uses **observed** JJA Niño 3.4 / DMI as a
  "perfect-forecast" proxy — an **upper bound** on prospective skill.
  A v1.3 release will reconstruct contemporaneous CPC/IRI forecast
  archives for an honest retrospective comparison.
- All four operational provider adapters (IRI / NOAA CPC / BoM)
  degrade gracefully to empty in this run; the BMKG manual-CSV
  template at `cache/bmkg_outlook.csv` is empty by default.
  The runtime stamps every Model D forecast row with
  `fallback_status=true` when this happens; the website displays
  a notice in the forecast section.
- Operational ENSO forecasts cover only ~9 overlapping 3-month seasons
  (~2.25 years). Years 2028–2030 are produced by persistence-decay
  toward the scenario prior — clearly labelled in
  `forecast_climate_stamps.csv` with `confidence="low"` and
  `source="persistence_decay"`.
- Pre-Model-D state is archived under `outputs/archive/pre_model_d_*/`
  and `docs/archive/pre_model_d_*/`; rollback via
  `git reset --hard backup/pre-model-d-forecast-upgrade`.

### Roadmap (v1.3)
- Scrape archived NOAA CPC / IRI ENSO forecasts (2018–2024) so Model D's
  historical CV uses contemporaneous forecasts rather than the
  perfect-forecast proxy.
- Wire up real IRI ENSO plume JSON parser and CPC HTML probability
  extractor once their endpoints stabilise.

---

## [v1.0.0] — 2026-05-13

### Added
- **Full analysis pipeline** for 150 kV SUTT Situbondo–Banyuwangi (281 towers, 2019–2025 data).
- **`tidy_data.py`** — automated preprocessing of messy 29-sheet Vaisala Excel workbook into 7 clean tidy CSVs; 35/35 data-quality checks pass; `_data_quality_report.txt` audit trail included.
- **`lightning_gfd_forecast.ipynb`** — reproducible Jupyter notebook (22 cells): data ingestion, ENSO/IOD climate fetching, Open-Meteo elevation per tower, three candidate models, leave-one-year-out + expanding-window cross-validation, 500-rep bootstrap × 3 climate-scenario uncertainty quantification.
- **Two-stage hybrid model (Model C)** as the primary forecast: line-level NB regression of annual total (AICc-selected) × per-tower empirical-Bayes shrunken share.
- **Per-tower climatology baseline (Model A)** reported alongside in all CV tables.
- **Model B (NB GLM + spatial spline smoother)** attempted; intentionally removed after catastrophic CV failure (expanding-window RMSE ~3,139 vs ~14 for A and C). Documented in notebook Section D and Excel README sheet.
- **Three ENSO climate scenarios** (La Niña / Neutral / El Niño) + equal-weight Marginalized envelope, 80% and 95% prediction intervals.
- **Interactive report website** (`docs/`) using `high-end-visual-design` (Editorial Luxury) taste-skill:
  - 4 Plotly interactive figures (annual totals + ENSO, seasonality, scenario forecast fan, top-20 bar)
  - 281-tower Leaflet hotspot map with layer control, per-tower popups, color-coded GFD scale
  - Scenario-tab switcher re-renders forecast figure in-place
  - Mobile-responsive (<768 px single-column collapse, floating nav with hamburger morph)
  - 0 console errors (browser-tested in Claude Preview)
  - Section 8 anti-pattern audit: all checks pass (no banned fonts, no harsh shadows, 16 cubic-bezier curves, backdrop-blur on fixed elements only, transform/opacity-only animations)
- **All 12 taste-skill skills** installed via `npx skills add https://github.com/Leonxlnx/taste-skill`.
- **`generate_site_data.py`** — builds 7 figure-data JSONs consumed by the website.
- **`docs/downloads/`** — one-click downloads: forecast Excel (13 sheets), standalone map HTML, top-20 CSV, sensitivity CSV, model-skill HTML, full notebook, tidy CSVs.
- **GitHub Pages ready** — site in `docs/` folder; enable via Settings → Pages → `main` `/docs`.

### Known limitations (documented in site section 06 and notebook)
- Model C beats climatology by only ~2% RMSE at n=7 years. Treat the climate-scenario fan as a sensitivity guide, not a skillful prediction.
- 2025 hold-out Pearson r = 0.237 (below the 0.6 verification target); per-tower spatial allocation is noisier than desired.
- Per-tower Vaisala density column is empirically ~5× the line-aggregate IEEE 1410 GFD; likely overlap-counted (each strike falls in ~5 adjacent towers' 3.125 km² circles). Verify convention with Vaisala before comparing to published climatologies.
- Decadal-scale climate trends are not modelled; re-run annually.

---

## Future versions

| Planned | Notes |
|---------|-------|
| v1.1.0 | Add 2026 lightning data when available; re-run model; report 2026 actuals vs forecast |
| v1.2.0 | Integrate Vaisala density convention clarification; rescale if overlap-counting is confirmed |
| v2.0.0 | Extend to multi-line coverage if additional Vaisala exports are available |
