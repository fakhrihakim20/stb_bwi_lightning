# VII. Limitations and Future Work

This paper is an operational case study, not a methodological
generalisation. Five limitations are material and we list them
explicitly.

**$n = 7$ years.** Every statistical claim above is conditional on
the lightning--climate relationship that held over 2019--2025
continuing to hold through 2030. The pipeline is correct *given* the
seven observations; no inference at $n = 7$ is conclusive. Adding
each successive year, especially via Model&nbsp;D's recency-weighted
fit, materially shifts the coefficient estimates. The first
prospective test will be the 2026 observed-versus-forecast comparison
in January 2027.

**Model&nbsp;D's historical CV is an upper bound on prospective skill.**
The cross-validation in &sect;V uses the *observed* JJA Niño&nbsp;3.4
and DMI values as if they had been perfectly forecast --- a
"perfect-forecast proxy". Real operational forecast skill will be
lower, because issued ENSO probability forecasts have non-trivial
error that the proxy does not capture. A planned v1.3 release will
reconstruct contemporaneous CPC/IRI archive forecasts for the
2018--2024 issuance period, enabling an honest retrospective
evaluation of Model&nbsp;D's prospective skill.

**The Vaisala per-tower density convention is unresolved.** As
documented in &sect;III, the per-tower count is empirically ~5$\times$
the line-aggregate unique-strike count, consistent with overlap
counting across adjacent 3.125&nbsp;km$^2$ collection circles. We work
at the panel scale throughout to keep prediction and observation on
the same units, but a half-hour conversation with Vaisala support
would permanently resolve whether per-tower counts should be
interpreted as overlap-counted or unique-attributed. This affects
the comparability of our absolute values --- not our model rankings
or rank-order recommendations --- against published external GFD
climatologies.

**Operational ENSO forecasts have a ~2.25-year horizon.** NOAA CPC
and IRI publish probability forecasts for approximately nine
overlapping 3-month seasons. Years 2028--2030 of Model&nbsp;D's output
are produced by persistence-decay toward the scenario prior with a
1.5-year time constant. These rows are clearly labelled in the
output's `forecast_climate_stamps.csv` with `confidence = "low"` and
`source = "persistence_decay"`, but they are not skillful.

**All operational climate adapters returned empty on this build.**
The forecast-informed framework described in &sect;IV.B is in place,
but at the time of publication no live forecast data has been
successfully fetched and parsed. Every Model&nbsp;D row in this
release carries `fallback_status = true` and reflects scenario priors
rather than agency outlooks. Live integration with the four providers
is the v1.3 roadmap; the BMKG path will be a user-maintained CSV by
design.

**Future work.** Beyond the v1.3 archive-forecast retrospective, the
two highest-leverage extensions are (i) extending the line set to the
full PLN UPT Probolinggo portfolio so that recency-weighted shrinkage
can borrow strength across corridors, and (ii) coupling the Stage&nbsp;2
allocation to a vegetation- and clearance-adjusted strike attribution
model to test whether the elevation-driven cluster at #137--#155 is
fully explained by topography or whether right-of-way features
contribute.
