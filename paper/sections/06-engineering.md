# VI. Engineering Implications

The dual-model framework lets PLN engineers ask two different
operational questions with the same data, separately. Four
recommendations follow directly from the results in &sect;V.

**Concentrate arrester upgrades on the 16-tower foothill cluster
common to both models.** The Jaccard 0.67 overlap is structural ---
both Model&nbsp;C (flat-weighted) and Model&nbsp;D (climate-forced) place
the same 16 towers between #137 and #155 in their top 20. This
cluster is the highest-GFD segment in every scenario, every year,
under either modelling assumption. Capex here has the strongest
expected return per rupiah of insulation-coordination investment.

**Tie maintenance scheduling to operational ENSO outlooks.** Model D
quantifies a **37&nbsp;%** La&nbsp;Niña-to-El&nbsp;Niño spread in 2026
line-mean GFD under forced-climate fit. BMKG and BoM publish ENSO
outlooks quarterly. In years leaning La&nbsp;Niña, pre-monsoon
inspections of insulators and earthing on the foothill section can
profitably be advanced by one to two months; in El&nbsp;Niño years,
that budget can be redirected to other lines or to capital projects.
This recommendation requires Model&nbsp;D's climate response, not
Model&nbsp;C's flat-average, even though Model&nbsp;C is the better
historical-fit benchmark.

**Use Model&nbsp;C for stable hotspot ranking; use Model&nbsp;D for
rolling annual planning.** This is the practical consequence of the
trade-off in Table&nbsp;1. Model&nbsp;C minimises historical
cross-validation error and is therefore the right tool when the
question is "which towers persistently take the most lightning over
the historical record?". Model&nbsp;D produces a meaningful operational
response to climate state and is therefore the right tool when the
question is "how should this year's maintenance budget shift under
the published ENSO outlook?". The website lets practitioners toggle
between the two models on both the hotspot map and the comparison
section.

**Re-run the entire analysis every January.** As 2026 data arrives,
the new sample size is $n = 8$; recency-weighted Model&nbsp;D is
especially sensitive to each new year because its half-life-three
weighting puts a normalised weight of approximately 1.8 on the most
recent year. The complete pipeline reruns in under ten minutes on
a laptop. The first comparison between Model&nbsp;D's 2026 forecast
and observed 2026 strikes will provide the first prospective skill
check that &sect;V was unable to provide retrospectively.
