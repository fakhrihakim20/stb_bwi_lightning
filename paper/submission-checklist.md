# Pre-submission checklist — ICT-PEP 2026

**Deadline: 30 June 2026** · Portal: <https://edas.info/N34860>

## Content

- [ ] Final author list confirmed
  *Current:* **Fakhri Hakim** (sole author)
  *Affiliation:* PT PLN (Persero), UPT Probolinggo, East Java, Indonesia
  *Email:* fakhrihakim20@gmail.com
- [ ] Title finalised
  *Current:* *"Per-Tower Lightning GFD Forecasting on the 150 kV Situbondo–Banyuwangi Transmission Line: A Dual-Model Hybrid Approach"*
- [ ] Abstract under 200 words (current: 195)
- [ ] All `[REFNEEDED:...]` markers in `refs.bib` resolved before final build
- [ ] All 14 audit rows in `paper/tables/audit.csv` still match live parquet/JSON
  (re-run `paper/tables/build_tables.py` after any model re-run)
- [ ] Co-author / supervisor review pass (if any) — sign-off recorded

## Compliance

- [ ] Paper compiles to 5–6 pages in IEEE A4 two-column Word template
- [ ] Local 7-gram similarity < 25 % against `docs/index.html`
  (last check: **1.6 %** — comfortable margin)
- [ ] iThenticate / Turnitin check (run via institutional account if available; ICT-PEP / IEEE may run their own)
- [ ] Figures embedded as PNG; resolution ≥ 300 dpi (current build: 300 dpi)
- [ ] All figure captions begin with "Fig. N." per IEEE style
- [ ] Tables follow IEEE table style (top + middle + bottom rules; sans-serif headers)
- [ ] References renumbered in order of appearance, IEEE numbered style

## Legal

- [ ] **IEEE eCF (electronic Copyright Form)** signed inside EDAS at submission time
  *Owner: Fakhri Hakim. PT PLN internal-approval pathway, if required, completed before EDAS upload.*
- [ ] Funding / acknowledgement footnote on page 1 if applicable
- [ ] Vaisala data clause: confirm internal PLN clearance to publish derived numbers from the FALLS export (consult data steward if uncertain)

## Build

- [ ] `python paper/tables/build_tables.py` — fresh tables
- [ ] `python paper/figures/build_figures.py` — fresh figures
- [ ] `python paper/similarity_check.py` — re-confirm < 25 %
- [ ] `python paper/build_docx.py` — generate `paper/paper-draft.docx`
  *(or `pandoc … --reference-doc=ieee-template.docx …` if pandoc is available)*
- [ ] Paste body into the official **IEEE A4 .DOC template** downloaded from <https://www.ieee.org/conferences/publishing/templates.html>
- [ ] Apply IEEE template heading / abstract / caption styles
- [ ] Final proofread

## Submit

- [ ] Upload `.docx` to EDAS <https://edas.info/N34860>
- [ ] Sign eCF in EDAS
- [ ] Submission ID and timestamp recorded here: ___________
