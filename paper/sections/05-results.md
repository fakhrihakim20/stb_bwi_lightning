# V. Cross-Validation and Results

## A. Cross-validation setup

Two complementary schemes are run for every model on every target.
**Leave-one-year-out (LOYO)** holds out one of the seven training years
at a time and predicts the held-out year from the remaining six.
**Expanding-window walk-forward** trains on the first $k$ years and
predicts year $k+1$, for $k$ from 3 to 6, simulating an operator who
re-fits the model each January with newly-arrived data. For each fold
we report mean absolute error (MAE), root mean squared error (RMSE),
and the continuous ranked probability score (CRPS). All metrics are
computed on the 281-tower panel, then averaged across folds.

## B. Skill comparison

Table&nbsp;1 reports the three metrics for the climatology baseline
(Model A), Model C, and Model D, on count and density targets, under
both CV schemes.

> **Table 1.** Cross-validation skill of Models A, C, D on count and
> density targets (LOYO and Expanding-window).

| Scheme | Target | Metric | A | C | D |
|---|---|---|---|---|---|
| LOYO | count | RMSE | 13.18 | **12.91** | 15.53 |
| LOYO | count | MAE | 10.75 | **10.64** | 12.85 |
| LOYO | count | CRPS | 8.88 | **8.76** | 9.54 |
| LOYO | density | RMSE | 4.21 | **4.13** | 4.96 |
| LOYO | density | MAE | 3.44 | **3.40** | 4.11 |
| LOYO | density | CRPS | 2.57 | **2.53** | 3.05 |
| Expanding | count | RMSE | 14.65 | **14.33** | 16.49 |
| Expanding | count | MAE | 12.08 | **12.02** | 14.39 |
| Expanding | count | CRPS | 10.08 | **10.01** | 10.82 |

Best in row in bold.

Two findings stand out. **First**, Model C improves over the
climatology baseline by a small but consistent margin --- about
**2&nbsp;%** on count RMSE in LOYO and 2&nbsp;% in expanding-window
--- in line with the size of effect that seven observations can
legitimately support. **Second**, Model D pays an explicit CV penalty:
its count RMSE is **15.53 versus 12.91 for Model C** in LOYO, a
**+20&nbsp;% increase**. This is the expected statistical cost of
forcing climate coefficients that AICc cannot justify at $n = 7$.
The penalty is *the* defining feature of the trade-off; it is not a
result we are trying to minimise but to characterise honestly.

## C. 2026 scenario response

The CV penalty buys something Model C cannot deliver: a meaningful
scenario response. Table&nbsp;2 reports Model D's 2026 line-mean GFD
forecast under three climate assumptions.

> **Table 2.** 2026 line-mean GFD forecast under Model D across three
> climate scenarios (mean across 281 towers, with 80&nbsp;% prediction
> intervals).

| Scenario | p50 | 80&nbsp;% PI |
|---|---|---|
| La Niña | 6.74 | [2.83, 19.54] |
| Neutral | 5.20 | [1.73,  9.09] |
| El Niño | 4.62 | [0.17, 15.66] |

The La&nbsp;Niña-to-El&nbsp;Niño spread is
$(6.74 - 4.62)/\mathrm{mean}(6.74, 4.62) = $ **37&nbsp;%**, and the
direction matches Indonesia's known wet/dry sensitivity to ENSO
[7,8]: La&nbsp;Niña years are wetter and produce more deep convection,
hence more lightning; El&nbsp;Niño years are drier and quieter. Under
the same scenarios Model C produces a spread of less than 5&nbsp;%,
because its line-level count formula collapsed to intercept-only
under AICc and the scenario inputs do not enter the prediction at all.
Figure&nbsp;2 visualises the scenario spread under Model&nbsp;D.

## D. Spatial concentration and rank agreement

Figure&nbsp;3 plots each model's top-20 highest-GFD towers under the
Neutral scenario as paired horizontal bars. The two top-20 lists
intersect in **16 towers**, giving a Jaccard overlap of
$|C \cap D|/|C \cup D| = $ **0.67**. The 16 overlap towers are all
clustered between towers #137 and #155, in the Mount Ijen foothills at
elevations of 210--245&nbsp;m. The four disagreements per side are at
the rank-20 boundary and reflect noise rather than substantive
spatial differences.

The operational implication is robust: **both models agree on which
cluster matters.** Methodological choices change rank order within
the foothill cluster but do not produce a different operational
recommendation.

## E. Where the models disagree, by tower

Figure&nbsp;4 plots the per-tower difference $\Delta_i =
\text{D}_i - \text{C}_i$ in 5-year-mean Neutral density against tower
elevation. Most towers fall on the mean-negative side of zero ---
Model&nbsp;D's forced climate coefficients compress the line-aggregate
forecast slightly below Model&nbsp;C's flat-weighted intercept under
Neutral conditions, regardless of elevation. The relationship between
$\Delta_i$ and elevation is essentially flat, which is what we expect:
the spatial ridge correction redistributes shares modestly without
introducing a systematic elevation bias.
