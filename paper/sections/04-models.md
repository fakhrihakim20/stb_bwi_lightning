# IV. Models

Both models share a two-stage structure: a line-level count regression
in Stage&nbsp;1, and a per-tower allocation in Stage&nbsp;2. They differ in
year-weighting, climate-variable handling, and spatial structure.

## A. Model C --- conservative benchmark

**Stage 1.** A Negative Binomial GLM is fitted to the line's
panel-aggregate annual count, with equal weight on each of the seven
years. The candidate predictor set is $\{\varnothing, \text{Niño}_{34},
\text{Niño}_{34}+\text{DMI}, \text{Niño}_{34}+\text{year}\}$ in JJA
units. AICc selects among these candidates. On the published v1.2
data AICc rejects every climate-augmented candidate at the available
sample size, so the selected formula is `count ~ 1` (intercept only)
and the fitted line total is the seven-year arithmetic mean.

**Stage 2.** Each tower's share-of-line is computed as a seven-year
mean of the observed per-tower fraction, then shrunk toward the
global mean via James--Stein with a shrinkage factor calibrated from
between-tower and within-tower variance. The shrunken shares re-
normalise to sum to one across the 281 towers.

**Uncertainty.** A 500-replicate year-block bootstrap is run for each
of three discrete climate scenarios (Niño&nbsp;3.4 fixed at $-1$, $0$,
$+1$); Negative Binomial process noise is added on top of each
deterministic prediction. 80&nbsp;% and 95&nbsp;% prediction intervals
are reported per tower per year.

## B. Model D --- forecast-informed extension

Model D retains the two-stage skeleton but adds three changes
designed to make climate variables a functional part of the model
rather than an AICc-eliminated candidate.

**Recency weighting.** Each historical year $t$ receives weight
$w_t = 0.5^{(T_{\max} - t)/h}$, normalised so $\sum_t w_t = 7$. The
half-life $h$ is selected by nested LOYO over $\{2, 3, 5, \infty\}$.
We replace ordinary sample size $n$ with Kish's effective sample size
$n_{\text{eff}} = \big(\sum_t w_t\big)^2 / \sum_t w_t^2$ wherever AICc
or shrinkage variance estimates are computed [5]. On the published
data $n_{\text{eff}} \approx 5.8$ at $h = 3$.

**Forced climate predictors.** AICc at $n_{\text{eff}} \approx 5.8$
declines to admit any climate variable into Model D either, for the
same reason it declines in Model C. We override the selection and
**lock** the count and kA formulas to
$\text{count} \sim \text{Niño}_{34}^{\text{JJA}} + \text{DMI}^{\text{JJA}}$.
This is the deliberate methodological choice that produces Model D's
climate response. We argue it is defensible because (i) the climate-
lightning coupling over the Maritime Continent is established
independently of this 7-year sample [7], and (ii) without the override
Model D collapses to a recency-weighted intercept that adds nothing
over Model C. The CV cost of the override is reported honestly in
&sect;V.

**Spatial ridge correction.** Each tower's log-share, after Stage&nbsp;2
shrinkage, is regressed via ridge [6] on three standardised features:
tower order along the line, tower elevation, and great-circle distance
to the Bali Strait. The ridge penalty $\alpha$ is tuned on the inner
LOYO loop alongside $h$. The corrected shares are re-normalised to
sum to one. We deliberately avoid splines: previous attempts at a
flexible spatial smoother at $n = 7$ exhibited perfect-separation
failures during expanding-window cross-validation.

**Forecast-informed climate inputs.** Model D consumes operational
ENSO outlooks where they exist (NOAA CPC, IRI, BoM, BMKG) and falls
back to documented persistence-decay toward the scenario prior beyond
the operational forecast horizon (~9 overlapping 3-month seasons).
Every Model D output row is stamped with `(provider, issued_date,
source_confidence, fallback_status)` so consumers can audit which
years carry live forecast information versus prior-driven persistence
decay. On the published build all four provider adapters returned
empty, so every Model D row in this release carries
`fallback_status = true`; live integration is on the v1.3 roadmap.

**Uncertainty.** A 200-replicate bootstrap is run for each scenario.
Each replicate resamples the seven training years with recency-weighted
probabilities, refits the full Model D pipeline, and produces a
deterministic per-tower prediction. Per-tower Negative Binomial
process noise is deliberately omitted; at the small per-tower mean
($\approx 15$ strikes) the heavy NB right tail dominates the empirical
mean of replicate samples and destroys interpretability. The reported
p50 is the median across replicates; the 80&nbsp;% and 95&nbsp;% bands
are the corresponding sample quantiles. These bands therefore reflect
parameter-plus-year-resampling uncertainty only, and are narrower than
Model C's process-noise-inclusive bands by construction.
