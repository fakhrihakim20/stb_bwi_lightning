# Per-Tower Lightning GFD Forecasting on the 150 kV Situbondo–Banyuwangi Transmission Line: A Dual-Model Hybrid Approach

**Fakhri Hakim**
PT PLN (Persero), UPT Probolinggo, East Java, Indonesia
*Email:* fakhrihakim20@gmail.com

---

**Word count target: 200 words ±10. Current: 195.**
**Framing: honest trade-off (Model D loses CV, wins climate response).**
**Every quantitative claim traced to `paper/tables/audit.csv` or named JSON.**

---

## Abstract

We present a per-tower lightning Ground Flash Density (GFD) forecast for the
281-tower **150 kV Situbondo–Banyuwangi** transmission line in East Java,
covering 2026–2030. Using seven years of Vaisala FALLS export data
(2019–2025; annual unique strikes ranged from **402 to 1,718**), we develop
two coexisting two-stage statistical hybrids: a **conservative benchmark
(Model C)** with equal annual weights and AICc-selected climate variables,
and a **forecast-informed extension (Model D)** that locks Niño 3.4 and
IOD-DMI as functional parameters and adds a ridge spatial correction over
tower order, elevation, and distance to coast. In leave-one-year-out cross-
validation, Model C achieves a count RMSE of **12.91** versus 13.18 for a
plain seven-year climatology; Model D, by forcing the climate coefficients
that AICc rejects at *n* = 7, trades **20 % higher RMSE (15.53)** for a
**37 % La Niña-to-El Niño scenario spread** in the 2026 line-mean forecast
(6.74 vs 4.62 flashes / km² / yr). Both models flag the same 16-tower
foothill cluster (Jaccard 0.67) at Mt. Ijen, 210–245 m elevation.
We argue the trade-off is intentional: Model C is the statistically-honest
benchmark; Model D is the planning instrument that responds to operational
ENSO outlooks. Code, data, and a public report are released openly.

---

## Numerical audit for the abstract (every quoted number traced)

| Claim in draft | Source |
|---|---|
| 281 towers, 150 kV Situbondo–Banyuwangi | `data_tidy/towers.csv` (281 rows); `README.md` line 4 |
| 2019–2025 (7 years) | `data_tidy/exposure_line_year.csv` year range |
| Unique strikes ranged 402 to 1,718 | `data_tidy/exposure_line_year.csv` rows for 2025 (402) and 2022 (1,718) |
| Model C count RMSE 12.91 | `paper/tables/audit.csv` row 2 |
| Model A count RMSE 13.18 | `paper/tables/audit.csv` row 1 |
| Model D count RMSE 15.53 | `paper/tables/audit.csv` row 3 |
| 20 % higher RMSE (Model D vs Model C) | (15.53 − 12.91) / 12.91 = 20.3 % |
| 37 % scenario spread | `paper/tables/audit.csv` row 10 (37.3 %) |
| 6.74 vs 4.62 flashes / km² / yr (La Niña vs El Niño) | `paper/tables/audit.csv` rows 7 and 9 |
| Jaccard 0.67 (16-tower overlap) | `paper/tables/audit.csv` row 11 |
| Mt. Ijen foothill cluster, 210–245 m | `data_tidy/towers.csv` joined with `cache/elevation.parquet`; in docs/index.html section 01 (verified) |

## What I deliberately did NOT claim

- "Model D beats Model C in CV" — false on the current data; abstract says the opposite.
- "Model D's prediction intervals are tighter / wider than Model C's" — true on disk but distracts from the central trade-off message; goes in §V of the body instead.
- Live forecast data was ingested — false; all Model D rows are `fallback_status=true`. Disclosed in §IV.B and §VII of the body.
- "Significantly" / "substantially" / other unquantified magnifiers — every comparative claim has an explicit number.

## Open questions for your review

1. **Word count:** the draft is currently 195 words. Acceptable, or do you want it tighter (~150) / longer (~250)?
2. **Author tone:** "we present / we develop / we argue" is the IEEE conference default. Switch to passive voice if institutional preference?
3. **Author list reference:** I've written "We present" without naming authors yet. Confirm the lead-author / co-author list separately before submission.
4. **The 20 % figure** is the headline negative number. If you want me to soften ("approximately 20 %") or sharpen ("a +20 % RMSE penalty") before drafting the rest, say so now.
5. **The "openly released" claim** is true (the GitHub repo is public). Confirm you want the repo URL in the abstract or only in §I.
