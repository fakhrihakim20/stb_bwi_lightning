# Paper draft — ICT-PEP 2026

This directory contains the conference paper draft for the
**International Conference on Technology and Policy in Energy & Electric Power
(ICT-PEP 2026)**, hosted by PT PLN (Persero) Research Institute,
22–24 September 2026 at ICE BSD Tangerang.

## Status

Under draft on branch `feature/paper-ict-pep-2026`. Not yet submitted.

## Source format

Drafts live in **Markdown** for ease of review and version control.
Final submission package is built as a Microsoft Word `.DOCX` via
`pandoc` against the official **IEEE A4 .DOC template** (Word-only;
no LaTeX template offered by ICT-PEP).

## Directory layout

| Path | Purpose |
|---|---|
| `abstract.md` | 200-word abstract |
| `sections/01-introduction.md` … `08-conclusion.md` | Section drafts |
| `figures/build_figures.py` | Re-renders all PNG figures from existing parquet/JSON |
| `figures/*.png` | Built figures (kept under version control for review) |
| `tables/build_tables.py` | Builds Table 1 (CV skill) and Table 2 (2026 scenario summary) |
| `tables/*.csv` `tables/*.md` | Table data + markdown render |
| `refs.bib` | BibTeX references (converted to IEEE style at build time) |
| `audit.md` | Numerical-claim audit: every quoted number traced to source file + cell |

## Submission targets

- **Page limit**: 5–6 pages (IEEE A4 two-column)
- **Similarity index**: ≤ 25 %
- **Deadline**: 30 June 2026
- **Portal**: EDAS — <https://edas.info/N34860>
- **Indexing**: IEEE Xplore (subject to scope and quality review)

## How to build the submission package (when ready)

1. `python tables/build_tables.py` — regenerate tables from current parquet
2. `python figures/build_figures.py` — regenerate all figures
3. `pandoc -o paper.docx --reference-doc=ieee-template.docx abstract.md sections/*.md`
4. Manual cleanup in Word (figure placement, table styles)
5. Save as `paper.docx`; upload to EDAS
</content>
</invoke>