#!/usr/bin/env python3
"""Extract the Amazon Pet Supplies styleguide PDF into a citable Markdown file.

This is a one-shot build step. Run it whenever data/PetSupplies_PetFood_*.pdf
changes; the output (data/amazon_styleguide_extracted.md) is what the skill
loads at recommendation time so it can cite rules by section and page.

Per the CommerceIQ assignment: the Pet Supplies styleguide is treated as
universal — its rules apply across all categories. Citations therefore name
the styleguide and page, not the category.

Usage:
    uv run .claude/skills/competitor-content-intelligence/scripts/extract_styleguide.py
    uv run .claude/skills/.../extract_styleguide.py --pdf path/to/other.pdf
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    print("ERROR: pypdf not installed. Run `uv sync` or `uv add pypdf`.",
          file=sys.stderr)
    sys.exit(1)

DEFAULT_PDF_NAME = "PetSupplies_PetFood_Styleguide_EN_AE._CB1198675309_.pdf"
DEFAULT_OUT_NAME = "amazon_styleguide_extracted.md"


def find_pdf(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"PDF not found: {p}")
        return p
    here = Path(__file__).resolve()
    for parent in [*here.parents]:
        candidate = parent / "data" / DEFAULT_PDF_NAME
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Could not locate data/{DEFAULT_PDF_NAME} from script location"
    )


def find_data_dir() -> Path:
    """Locate the project-root data/ directory (where the output MD goes)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        d = parent / "data"
        if d.exists() and (d / DEFAULT_PDF_NAME).exists():
            return d
    raise FileNotFoundError("Could not locate project-root data/ directory")


def _clean_line(line: str) -> str:
    """Collapse runs of whitespace and strip control chars."""
    line = line.replace(" ", " ")
    line = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", line)
    line = re.sub(r"[ \t]+", " ", line)
    return line.strip()


def extract(pdf_path: Path) -> str:
    """Return a Markdown document with one `## Page N` block per page.

    The point isn't pretty formatting — it's that downstream prompts can
    cite "Pet Supplies Styleguide, p. 12" and a reader can map it back to
    the source PDF deterministically.
    """
    reader = PdfReader(str(pdf_path))
    n_pages = len(reader.pages)

    out_lines = [
        f"# Amazon Pet Supplies Styleguide (EN-AE) — Extracted",
        "",
        f"> Source: `{pdf_path.name}` ({n_pages} pages).",
        "> Extracted with `pypdf` from the PDF CommerceIQ provided for the take-home.",
        "> Per the assignment, treat these rules as applying to all product categories",
        "> (Pet Supplies, Beverages, Sports Nutrition, etc.) — not just Pet Supplies.",
        "",
        "Each section below is one page of the source PDF. Citations should reference",
        "the page number (e.g., *Amazon Pet Supplies Styleguide, p. 12*) so a reader",
        "can map the rule back to the original document.",
        "",
        "---",
        "",
    ]

    for idx, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception as e:
            print(f"WARN: page {idx} extraction failed ({e})", file=sys.stderr)
            raw = ""
        cleaned = [_clean_line(line) for line in raw.splitlines()]
        cleaned = [line for line in cleaned if line]
        out_lines.append(f"## Page {idx}")
        out_lines.append("")
        if not cleaned:
            out_lines.append("_(no extractable text on this page — likely image-only)_")
        else:
            out_lines.extend(cleaned)
        out_lines.append("")
        out_lines.append("---")
        out_lines.append("")

    return "\n".join(out_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Amazon styleguide PDF to Markdown")
    parser.add_argument("--pdf", help="Path to the source PDF (default: data/PetSupplies_PetFood_...pdf)")
    parser.add_argument("--out", help=f"Output path (default: data/{DEFAULT_OUT_NAME})")
    args = parser.parse_args()

    pdf_path = find_pdf(args.pdf)
    out_path = Path(args.out).expanduser().resolve() if args.out else find_data_dir() / DEFAULT_OUT_NAME

    print(f"Reading: {pdf_path}", file=sys.stderr)
    md = extract(pdf_path)
    out_path.write_text(md)
    print(f"Wrote:   {out_path} ({len(md):,} chars)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
