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
3. `python similarity_check.py` — local 7-gram overlap vs docs/index.html (target < 25 %; current pass: 1.6 %)
4. **DOCX conversion** — pick one path:

   - **Path A (recommended if pandoc is available)**:

     ```
     pandoc -o paper.docx --reference-doc=ieee-template.docx \
         abstract.md sections/*.md
     ```

     The `--reference-doc` flag applies the official IEEE Word
     template styles. Pandoc is **not installed in this development
     environment**; install from <https://pandoc.org> if you have
     it available.

   - **Path B (python-docx fallback, used here)**:

     ```
     pip install --user python-docx
     python build_docx.py
     ```

     Produces `paper/paper-draft.docx` with default Word styles.
     Open the IEEE A4 .DOC template from
     <https://www.ieee.org/conferences/publishing/templates.html>
     and copy the body of the draft into the template manually,
     re-applying the template's heading / abstract / caption styles.

5. Insert figure PNGs (`figures/*.png`) and the two tables (`tables/*.md`)
   into the appropriate Word locations.
6. Add the author list, affiliations, and copyright statement directly
   in the IEEE template — these are deliberately not in the markdown
   source because they vary by submission.
7. Save as `paper.docx`; upload to EDAS (<https://edas.info/N34860>).
</content>
</invoke>