"""Concatenate all paper sections into a single Microsoft Word .docx.

This script produces a *basic* .docx with default Word styling. The
ICT-PEP submission requires the **official IEEE A4 .DOC template** at
<https://www.ieee.org/conferences/publishing/templates.html>. The
manual step after running this script: open the IEEE template in
Word, copy the body content from `paper/paper-draft.docx` into the
template's content body, and re-apply the template's heading /
abstract / figure-caption styles.

This is the cleanest path that avoids fabricating IEEE styles in
code. Pandoc with `--reference-doc=ieee-template.docx` would automate
the style application, but pandoc is not installed in this
environment.

Usage:
    pip install --user python-docx   # one-time
    python paper/build_docx.py

Output:
    paper/paper-draft.docx           # plain Word doc, no IEEE styles
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECTIONS = HERE / "sections"
ABSTRACT = HERE / "abstract.md"
FIGURES = HERE / "figures"
TABLES = HERE / "tables"
OUT = HERE / "paper-draft.docx"

try:
    from docx import Document
    from docx.shared import Inches, Pt
except ImportError:
    print("ERROR: python-docx not installed.")
    print("Install with: pip install --user python-docx")
    sys.exit(2)


def add_markdown(doc: "Document", text: str) -> None:
    """Add a markdown blob to the doc with basic formatting.

    Handles: headings (#, ##, ###), bold (**...**), italics (*...*),
    code (`...`), bullet lists, and paragraph breaks. Does not handle
    tables, footnotes, or inline math (those need the IEEE template
    pass in Word). LaTeX-style $...$ math is passed through as plain
    text and should be re-typeset in Word.
    """
    import re

    paragraphs = re.split(r"\n\s*\n", text.strip())
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # Heading
        m = re.match(r"^(#{1,4})\s+(.*)$", para)
        if m:
            level = len(m.group(1))
            doc.add_heading(m.group(2).strip(), level=level)
            continue
        # Bullet list
        if para.startswith(("* ", "- ")):
            for line in para.split("\n"):
                if line.strip().startswith(("* ", "- ")):
                    doc.add_paragraph(line.strip()[2:].strip(), style="List Bullet")
            continue
        # Normal paragraph — strip markdown emphasis markers
        text = para.replace("\n", " ")
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\[\^[^\]]+\]", "", text)  # drop footnote refs
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            doc.add_paragraph(text)


def main() -> None:
    doc = Document()
    # Title block
    doc.add_heading("Per-Tower Lightning GFD Forecasting on the 150 kV "
                    "Situbondo–Banyuwangi Transmission Line: "
                    "A Dual-Model Hybrid Approach", level=0)
    doc.add_paragraph("Fakhri Hakim")
    doc.add_paragraph("PT PLN (Persero), UPT Probolinggo, East Java, Indonesia")
    doc.add_paragraph("Email: fakhrihakim20@gmail.com")
    doc.add_paragraph("")

    # Abstract
    abstract_text = ABSTRACT.read_text(encoding="utf-8")
    # Drop the audit / open-questions sections at the bottom of abstract.md
    abstract_body = abstract_text.split("\n## Numerical audit")[0]
    abstract_body = abstract_body.split("\n## Draft\n", 1)[-1]
    doc.add_heading("Abstract", level=1)
    add_markdown(doc, abstract_body)
    doc.add_paragraph("")

    # Body sections
    for section_file in sorted(SECTIONS.glob("*.md")):
        add_markdown(doc, section_file.read_text(encoding="utf-8"))
        doc.add_paragraph("")

    # Append a marker so the manual paste-into-IEEE-template step is obvious
    doc.add_paragraph("")
    doc.add_paragraph("=== END OF DRAFT — paste body above into IEEE template ===")
    doc.add_paragraph(f"Figures (PNGs) in {FIGURES}, tables in {TABLES}.")

    doc.save(OUT)
    print(f"  wrote {OUT}")
    print()
    print(f"  Next: open the IEEE A4 .DOC template from")
    print(f"        https://www.ieee.org/conferences/publishing/templates.html")
    print(f"  and copy the body of this .docx into the template,")
    print(f"  re-applying the template's heading / abstract / caption styles.")


if __name__ == "__main__":
    main()
