# Lightning GFD Forecast — 150 kV Situbondo–Banyuwangi (2026–2030)

A study of seven years of Vaisala-format lightning data on the
**150 kV SUTT Situbondo–Banyuwangi** transmission line, with a five-year
forward forecast of per-tower Ground Flash Density for every one of the
**281 towers** on the line, under three explicit climate scenarios
(La Niña / Neutral / El Niño).

The report is written for engineers and PLN decision-makers — not
data scientists. Every chart is interactive. Every assumption is stated.
Every caveat sits in a dedicated section, not in a footnote.

---

## View the report

**Option A — Online (GitHub Pages):**
After enabling Pages in this repository (Settings → Pages → Source:
`main` branch, `/docs` folder), the report is live at
<https://fakhrihakim20.github.io/stb_bwi_lightning/>.

**Option B — Locally:** clone this repository and either
1. open `docs/index.html` directly in a modern browser, **or**
2. run a tiny static server to enable the interactive map / charts:

```bash
cd docs
python -m http.server 8080
# then open http://localhost:8080
```

---

## What is in this repository

| Path | Contents |
|------|----------|
| `docs/` | The static report website (HTML / CSS / JS) — interactive figures, map, and downloads. This is what GitHub Pages serves. |
| `docs/downloads/` | All operational deliverables: forecast Excel, standalone map, top-20 CSV, sensitivity table, model-skill report, full Jupyter notebook, tidy CSVs. |
| `lightning_gfd_forecast.ipynb` | The complete reproducible analysis. Open in Jupyter Lab / VS Code to re-run every cell. |
| `tidy_data.py` | One-shot preprocessing — converts the messy 29-sheet Excel workbook into seven clean tidy CSVs. Run before the notebook. |
| `build_notebook.py` | Helper that constructs the notebook from inline cell definitions (so the analysis is version-controlled as plain Python). |
| `generate_site_data.py` | Builds the JSON data files in `docs/figures/` from the model outputs (used by the website's charts). |
| `data_tidy/` | The seven tidy CSVs plus a human-readable data-quality audit report. |
| `outputs/` | Raw model outputs (forecast parquet, CV results, map HTML, Excel, CSVs). |
| `cache/` | Cached external data (NOAA Niño 3.4, IOD DMI, Open-Meteo elevation). Lets the analysis re-run offline. |

The source Excel workbooks (`Lightning Exposure Line ... .xlsx`,
`koordinat tower srintami.xlsx`) are also kept at the root so the
pipeline is end-to-end reproducible.

---

## Re-running the analysis

```bash
# 1. Install Python dependencies (one-time)
pip install pandas numpy scipy statsmodels scikit-learn patsy \
            openpyxl requests plotly folium joblib nbformat jupyter

# 2. Run the preprocessing
python tidy_data.py        # writes data_tidy/*.csv (1–2 sec)

# 3. (Optional) Rebuild the notebook from build_notebook.py
python build_notebook.py   # writes lightning_gfd_forecast.ipynb

# 4. Execute the notebook end-to-end
python -m jupyter nbconvert --to notebook --execute \
    lightning_gfd_forecast.ipynb \
    --output lightning_gfd_forecast.executed.ipynb \
    --ExecutePreprocessor.timeout=900

# 5. Refresh the website data
python generate_site_data.py
```

Every step caches its external API calls. After the first run with
network, every subsequent run is offline-reproducible.

---

## Method, in one paragraph

The forecast is a **two-stage statistical hybrid (Model C)**. Stage 1
fits a Negative Binomial regression of the line's annual unique-strike
total on lagged ENSO (Niño 3.4) and IOD (DMI) climate indices, with
AICc model selection. Stage 2 distributes that line-level total across
the 281 towers using each tower's empirical-Bayes-shrunken share of
historical strikes. Uncertainty is propagated through a 500-replicate
year-block bootstrap × three climate scenarios → 80 % and 95 %
prediction intervals per tower per year. A plain climatology baseline
(Model A) is reported alongside in every cross-validation table. A
Negative-Binomial GLM with spatial spline smoother (Model B) was
attempted, failed expanding-window CV due to perfect separation at
n = 7 years, and was intentionally removed from all deliverables.

Full details, model skill numbers, and honest limitations are in the
report's **section 04 (Method)**, **section 06 (Caveats)**, and the
notebook's Section E.

---

## Honest caveats

This is research-grade, not gospel. Treat the forecast as a
**sensitivity guide**, not a precise prediction.

- Model C beats a plain seven-year climatology by **~2 % RMSE** in
  cross-validation — small absolute gain at n = 7.
- The 2025 hold-out test gave Pearson r ≈ 0.24, below the 0.6 target
  we set in the plan.
- The Vaisala per-tower density convention is empirically ~5× the line
  aggregate. Most likely cause: per-tower counts are overlap-counted
  (each strike falls within ~5 adjacent towers' 3.125 km² circles).
  **Confirm with Vaisala support before benchmarking against
  published GFD climatologies.**
- Decadal-scale climate trends are not modelled. Re-run annually.

---

## License & attribution

Internal PLN research. The lightning data is licensed to PLN by
Vaisala. The analysis code, methodology, and report are open for
internal use within PLN. External climate indices are public
(NOAA PSL, BoM). Map tiles by CARTO / OSM contributors.

Built with open-source tools: Python, statsmodels, scikit-learn,
Plotly, Leaflet, folium. UI direction guided by the
[taste-skill](https://github.com/leonxlnx/taste-skill) Agent Skill
framework (Editorial Luxury vibe).
