# Changelog

All notable changes to the Lightning GFD Forecast project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
