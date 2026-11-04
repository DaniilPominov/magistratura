#!/usr/bin/env python3
"""Extract text from PDFs into Markdown pages for the wiki.

For every PDF in ``wiki/docs`` this script:

* uses the embedded text layer when one is present (PyMuPDF blocks);
* falls back to OCR with Tesseract (rus+eng) for scanned documents;
* writes ``<same name>.md`` next to the PDF.

Run from the repository root or from ``magister_work/wiki``::

    python tools/pdf2md.py

Requirements: PyMuPDF (``pip install pymupdf``) and, for scanned
documents, a Tesseract installation with the Russian language data.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("PyMuPDF is required: pip install pymupdf")

# Minimum average number of characters per page (sampled pages) for the
# PDF to be treated as having a usable text layer.
TEXT_LAYER_MIN_CHARS_PER_PAGE = 100
# How many pages to sample when deciding whether a text layer exists.
TEXT_LAYER_SAMPLE_PAGES = 5

# Traineddata folders searched for the Russian model.
TESSDATA_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Tesseract-OCR" / "tessdata",
    Path(r"C:\Program Files\Tesseract-OCR") / "tessdata",
]

TESSERACT_CANDIDATES = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path("tesseract"),
]

# Lines that are only page numbers or running footers.
FOOTER_RE = re.compile(r"^[\s\d\-–—_.·]*$")


def find_tesseract() -> str | None:
    for candidate in TESSERACT_CANDIDATES:
        resolved = shutil.which(str(candidate)) if candidate.name == "tesseract" else candidate
        if resolved and Path(resolved).exists():
            return str(resolved)
    return shutil.which("tesseract")


def find_tessdata() -> Path | None:
    """Prefer a tessdata folder that contains the Russian model."""
    available = [c for c in TESSDATA_CANDIDATES if c.is_dir()]
    for candidate in available:
        if (candidate / "rus.traineddata").exists():
            return candidate
    for candidate in available:
        if any(candidate.glob("*.traineddata")):
            return candidate
    return None


def dehyphenate(text: str) -> str:
    """Join words split across a line break with a trailing hyphen."""
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


def clean_line(line: str) -> str:
    line = line.replace("\u00a0", " ").replace("\u00ad", "")
    return re.sub(r"[ \t]+", " ", line).strip()


def block_to_paragraph(block_text: str) -> str:
    """Collapse a raw block (with hard line breaks) into one paragraph."""
    text = dehyphenate(block_text)
    lines = [clean_line(ln) for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return ""
    return " ".join(lines)


def extract_text_layer(doc: fitz.Document) -> list[str]:
    """Return Markdown body assembled from the PDF text layer."""
    paragraphs: list[str] = []
    for page in doc:
        for block in page.get_text("blocks"):
            text = block[4]
            if not text or not text.strip():
                continue
            if FOOTER_RE.match(text):
                continue
            paragraph = block_to_paragraph(text)
            if paragraph:
                paragraphs.append(paragraph)
    return paragraphs


def ocr_languages(tessdata: Path) -> str:
    """Pick the best available language set, preferring Russian + English."""
    present = {p.stem for p in tessdata.glob("*.traineddata")}
    langs = [l for l in ("rus", "eng") if l in present]
    return "+".join(langs) if langs else "eng"


def ocr_pages(doc: fitz.Document, tesseract: str, tessdata: Path) -> list[str]:
    """OCR every page and return one paragraph block per page."""
    env = dict(os.environ)
    env["TESSDATA_PREFIX"] = str(tessdata)
    language = ocr_languages(tessdata)
    paragraphs: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for index, page in enumerate(doc):
            pix = page.get_pixmap(dpi=300)
            image = Path(tmp) / f"page-{index:04d}.png"
            pix.save(image)
            out_base = Path(tmp) / f"page-{index:04d}"
            subprocess.run(
                [
                    tesseract,
                    str(image),
                    str(out_base),
                    "-l",
                    language,
                    "--psm",
                    "1",
                ],
                check=True,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            raw = out_base.with_suffix(".txt").read_text(encoding="utf-8")
            page_paragraphs = split_ocr_paragraphs(raw)
            paragraphs.extend(page_paragraphs)
    return paragraphs


def split_ocr_paragraphs(raw: str) -> list[str]:
    """Split an OCR page into paragraphs on blank lines."""
    paragraphs = []
    current: list[str] = []
    for line in raw.splitlines():
        cleaned = clean_line(line)
        if cleaned:
            current.append(cleaned)
        elif current:
            paragraphs.append(dehyphenate("\n".join(current)))
            current = []
    if current:
        paragraphs.append(dehyphenate("\n".join(current)))
    return paragraphs


def has_text_layer(doc: fitz.Document) -> bool:
    """Decide whether the PDF carries a usable text layer.

    Scanned documents often have a sparse cover page, so sample several
    pages spread across the document and require an average of
    ``TEXT_LAYER_MIN_CHARS_PER_PAGE`` characters per page.
    """
    if doc.page_count == 0:
        return False
    count = min(TEXT_LAYER_SAMPLE_PAGES, doc.page_count)
    step = max(1, doc.page_count // count)
    indices = list(range(0, doc.page_count, step))[:count]
    total = sum(len(doc[i].get_text("text").strip()) for i in indices)
    return total / len(indices) >= TEXT_LAYER_MIN_CHARS_PER_PAGE


def render_markdown(title: str, source: str, method: str, paragraphs: list[str]) -> str:
    header = (
        "---\n"
        f'title: "{title}"\n'
        f'source: "{source}"\n'
        f"extraction: {method}\n"
        f"extracted: {date.today().isoformat()}\n"
        "---\n\n"
        f"# {title}\n\n"
        "> Полный текст документа, извлечённый из PDF. "
        "Исходник: `" + source + "`.\n\n"
    )
    body = "\n\n".join(paragraphs)
    return header + body + "\n"


def convert(pdf: Path, out_dir: Path) -> Path:
    doc = fitz.open(pdf)
    try:
        if has_text_layer(doc):
            method = "text-layer (PyMuPDF)"
            paragraphs = extract_text_layer(doc)
        else:
            tesseract = find_tesseract()
            if not tesseract:
                sys.exit("Tesseract not found, but OCR is required for " + pdf.name)
            tessdata = find_tessdata()
            if not tessdata:
                sys.exit("No tessdata folder with traineddata found.")
            method = "ocr (Tesseract rus+eng)"
            paragraphs = ocr_pages(doc, tesseract, tessdata)
    finally:
        doc.close()

    markdown = render_markdown(pdf.stem, pdf.name, method, paragraphs)
    target = out_dir / f"{pdf.stem}.md"
    target.write_text(markdown, encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    wiki_dir = Path(__file__).resolve().parent.parent
    parser.add_argument("docs", nargs="*", type=Path, default=None,
                        help="PDF files to convert (default: all in docs/)")
    parser.add_argument("--docs-dir", type=Path, default=wiki_dir / "docs")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Output folder (default: same as docs)")
    args = parser.parse_args()

    out_dir = args.out_dir or args.docs_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    pdfs = args.docs or sorted(args.docs_dir.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"No PDFs found in {args.docs_dir}")

    for pdf in pdfs:
        target = convert(pdf, out_dir)
        size = target.stat().st_size
        print(f"{pdf.name} -> {target.name} ({size} bytes)")


if __name__ == "__main__":
    main()
