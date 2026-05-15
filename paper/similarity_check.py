"""Local similarity check: paper draft vs docs/index.html.

This is NOT iThenticate. It is a local 7-gram shingle-overlap check
that flags near-verbatim copy-paste between the paper sections and
the website prose. The website is your own work, so high overlap is
not plagiarism — but ICT-PEP's 25 % similarity index will likely
penalise it. iThenticate's commercial product uses the same shingle
technique; this script gives a first-pass estimate that catches the
obvious copies before submission.

Usage:
    python paper/similarity_check.py

Output:
    - Per-section shingle-overlap percentage against docs/index.html
    - Top matching shingles (the actual repeated phrases)
"""

from __future__ import annotations

import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


class HTMLTextExtractor(HTMLParser):
    """Strip HTML tags and yield only the rendered text content."""
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._chunks.append(data)

    @property
    def text(self) -> str:
        return " ".join(self._chunks)


def normalise(text: str) -> str:
    """Lowercase, strip markdown/HTML markup, collapse whitespace."""
    # Remove markdown code fences and inline code
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    # Remove markdown link/emphasis syntax but keep the visible text
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Strip HTML entities & punctuation
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def shingles(text: str, n: int = 7) -> Counter:
    tokens = text.split()
    return Counter(" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def jaccard(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / max(union, 1)


def overlap_fraction(paper: Counter, site: Counter) -> float:
    """What fraction of the paper's shingles also appear in the site?"""
    if not paper:
        return 0.0
    shared = sum(c for s, c in paper.items() if s in site)
    return shared / sum(paper.values())


def main() -> None:
    repo = Path(__file__).resolve().parent.parent
    site_html = (repo / "docs" / "index.html").read_text(encoding="utf-8")
    p = HTMLTextExtractor()
    p.feed(site_html)
    site_text = normalise(p.text)
    site_shingles = shingles(site_text)

    print(f"docs/index.html: {len(site_shingles):,} unique 7-gram shingles\n")
    print(f"{'Section':<32} {'shingles':>10} {'overlap_%':>10}  shared_shingles")
    print("-" * 88)

    sections = sorted((repo / "paper" / "sections").glob("*.md"))
    files = [(repo / "paper" / "abstract.md")] + sections

    grand_total_shared = 0
    grand_total_paper = 0
    for f in files:
        text = normalise(f.read_text(encoding="utf-8"))
        sh = shingles(text)
        if not sh:
            print(f"{f.name:<32} {0:>10} {'n/a':>10}")
            continue
        overlap = overlap_fraction(sh, site_shingles)
        shared = sum(c for s, c in sh.items() if s in site_shingles)
        grand_total_shared += shared
        grand_total_paper += sum(sh.values())
        print(f"{f.name:<32} {len(sh):>10,} {100*overlap:>9.1f}% {shared:>10,}")

    grand_pct = 100 * grand_total_shared / max(grand_total_paper, 1)
    print("-" * 88)
    print(f"{'PAPER TOTAL':<32} {grand_total_paper:>10,} {grand_pct:>9.1f}% {grand_total_shared:>10,}")
    print()
    print(f"ICT-PEP similarity ceiling: 25 %  ->  {'PASS' if grand_pct < 25 else 'OVER'}  "
          f"(this is a local first-pass; iThenticate is the official check)")

    # Show top 10 repeated phrases for the highest-overlap section
    print("\nMost-repeated 7-gram phrases across paper that also appear in site:")
    all_paper_shingles = Counter()
    for f in files:
        all_paper_shingles.update(shingles(normalise(f.read_text(encoding="utf-8"))))
    shared = {s: c for s, c in all_paper_shingles.items() if s in site_shingles}
    for s, c in sorted(shared.items(), key=lambda x: -x[1])[:12]:
        print(f"  ×{c}  \"{s}\"")


if __name__ == "__main__":
    main()
