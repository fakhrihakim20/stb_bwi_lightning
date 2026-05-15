# I. Introduction

Lightning is the dominant cause of unplanned outages on tropical
150&nbsp;kV transmission lines. Traditional insulation-coordination
practice relies on a single regional Ground Flash Density (GFD)
figure drawn from IEEE&nbsp;1410 [1] or IEEE&nbsp;1243 [2], which
collapses the spatial heterogeneity of a real corridor into a scalar.
For an operator deciding where to upgrade arresters or how to phase
pre-monsoon inspections, a single scalar is insufficient: the question
is *which tower* and *which year*.

The 150&nbsp;kV SUTT Situbondo--Banyuwangi line in East Java illustrates
the gap. Across the seven years 2019--2025, Vaisala FALLS unique-strike
counts on the line ranged from **402 (2025) to 1,718 (2022)** --- a
**fourfold swing** [^a1]. Across towers, the historical seven-year
mean per-tower density spans **2.88 to 10.78 flashes/km²/yr** ---
a 3.7$\times$ ratio between the lowest coastal tower and the
highest-elevation foothill tower.
A flat regional GFD therefore systematically under-provisions some
towers and over-provisions others, in different years.

This paper contributes a reproducible per-tower forecasting pipeline
and an honest dual-model comparison framework, applied to the
281-tower Situbondo--Banyuwangi corridor for the 2026--2030 horizon.
Two coexisting two-stage statistical hybrids are released side by side:

* **Model C** --- a conservative benchmark. Stage&nbsp;1 fits a Negative
  Binomial regression to the line's annual count with AICc-selected
  climate predictors; Stage&nbsp;2 distributes the line total to towers
  via empirical-Bayes James--Stein shrunken shares.
* **Model D** --- a forecast-informed extension. Same two-stage structure
  but with Niño&nbsp;3.4 and IOD-DMI **forced as functional parameters**
  (overriding the AICc rejection), recency weighting, and a low-degree
  ridge spatial correction on tower order, elevation, and distance to
  coast.

We frame the contribution as a transparent trade-off, not a
benchmark-beating claim. On leave-one-year-out cross-validation Model&nbsp;C
attains a count RMSE of **12.91** flashes versus 13.18 for a plain
seven-year climatology; Model&nbsp;D pays a **20&nbsp;% RMSE penalty
(15.53)** but produces a **37&nbsp;% La&nbsp;Niña-to-El&nbsp;Niño scenario
spread** in 2026 line-mean GFD where Model&nbsp;C produces essentially
none. The two models answer different operational questions and we
publish both so practitioners can pick their assumption transparently.
All code, data, and the public report are released openly [12].

[^a1]: All quantitative claims in this paper are traced to specific
file paths and aggregation rules in `paper/tables/audit.csv` of the
source repository.
