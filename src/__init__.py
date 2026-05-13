"""src/ — Model D extension package for the Lightning GFD forecast.

Modules:
    recency           — recency-weighting utilities (exponential half-life)
    climate_forecast  — forecast-informed climate adapter (IRI/CPC/BoM/BMKG)
    models_d          — Model D fit, predict, bootstrap
    cv_d              — nested-LOYO cross-validation for Model D

Model C (the conservative benchmark) lives inline in build_notebook.py and is
not touched by this package. Model D imports and reuses Model C's helpers
where appropriate but produces independent outputs.
"""

__version__ = "0.1.0"
