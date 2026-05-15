# II. Related Work

**Operational lightning GFD.** IEEE&nbsp;1410 [1] and IEEE&nbsp;1243 [2]
remain the engineering reference for converting strike density into
expected flashover rates on overhead lines. Their default GFD inputs
are regional averages drawn from satellite climatologies such as
OTD/LIS [10] and the WWLLN-based maps of Albrecht et al. [8]. None of
these references treats GFD as a tower-resolved quantity that varies
year on year with climate state.

**Statistical modelling of overdispersed lightning counts.** Annual
strike counts at a fixed location are textbook overdispersed: the
sample variance routinely exceeds the mean by an order of magnitude.
We follow the Negative Binomial regression treatment of Hilbe [3],
which has become the default for ecological and atmospheric count
data over the past two decades.

**Small-sample shrinkage.** With only seven temporal observations per
tower, raw per-tower means are dominated by sampling noise. The
James--Stein shrinkage estimator [4] reduces mean squared error
uniformly over independent normal estimators when more than two are
combined. Our Stage&nbsp;2 share calculation adapts this to a
log-share scale with a global-mean target.

**Climate--lightning coupling in the maritime continent.** Indonesian
rainfall is well established as bimodal between regions, with ENSO
explaining a substantial share of interannual variance over the
eastern monsoonal zone that contains our study line [7].
[REFNEEDED:Indonesia-specific lightning-ENSO study, if available].
We treat this empirically by including Niño&nbsp;3.4 and the IOD-DMI
as predictors and reporting whether AICc accepts them at our sample
size; the answer for $n = 7$ is "no", which motivates Model D's
override.

**Why not deep learning.** Spatio-temporal neural approaches such as
DeepKriging require training-set sizes that exceed our seven annual
observations by two to three orders of magnitude. The "recency
weighting" component of Model D is implemented as classical
exponential sample weighting --- not as a neural attention mechanism
--- and uses Kish's effective sample size [5] to compute AICc penalties
honestly under non-uniform weights. We treat ridge regression [6] in
Stage&nbsp;2 the same way: a regularised linear smoother whose degrees
of freedom can be bounded analytically.
