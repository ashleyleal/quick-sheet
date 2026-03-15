"""
app/ingestion/pdf_parser.py
Extracts text from PDFs page-by-page using PyMuPDF (fitz).
Falls back to pdfplumber for pages where PyMuPDF produces poor output.
"""
 
import io
from pathlib import Path
from typing import Union
 
# PyMuPDF
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
 
# pdfplumber fallback
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
 
 
def extract_pages(source: Union[str, Path, bytes]) -> dict[int, str]:
    """
    Extract text from a PDF, returning a dict of {page_number: text}.
    Page numbers are 1-indexed.
 
    Args:
        source: file path, Path object, or raw bytes of a PDF
 
    Returns:
        dict mapping page number (1-indexed) to extracted text string
    """
    if isinstance(source, (str, Path)):
        raw_bytes = Path(source).read_bytes()
    else:
        raw_bytes = source
 
    pages: dict[int, str] = {}
 
    if PYMUPDF_AVAILABLE:
        pages = _extract_with_pymupdf(raw_bytes)
    elif PDFPLUMBER_AVAILABLE:
        pages = _extract_with_pdfplumber(raw_bytes)
    else:
        raise ImportError(
            "No PDF extraction library found. "
            "Install PyMuPDF: pip install PyMuPDF"
        )
 
    # For any page where PyMuPDF gave very little text, try pdfplumber
    if PYMUPDF_AVAILABLE and PDFPLUMBER_AVAILABLE:
        thin_pages = [p for p, t in pages.items() if len(t.strip()) < 50]
        if thin_pages:
            fallback = _extract_with_pdfplumber(raw_bytes)
            for p in thin_pages:
                if fallback.get(p, "").strip():
                    pages[p] = fallback[p]
 
    return pages
 
 
def extract_full_text(source: Union[str, Path, bytes]) -> str:
    """
    Convenience method: extract all pages and join into one string.
    Pages are separated by a form-feed character (\f).
    """
    pages = extract_pages(source)
    return "\f".join(pages[i] for i in sorted(pages.keys()))
 
 
def get_page_count(source: Union[str, Path, bytes]) -> int:
    """Return total number of pages in the PDF."""
    if isinstance(source, (str, Path)):
        raw_bytes = Path(source).read_bytes()
    else:
        raw_bytes = source
 
    if PYMUPDF_AVAILABLE:
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        return len(doc)
    elif PDFPLUMBER_AVAILABLE:
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            return len(pdf.pages)
    return 0
 
 
# ── Private helpers ───────────────────────────────────────────────────────────
 
def _extract_with_pymupdf(raw_bytes: bytes) -> dict[int, str]:
    doc = fitz.open(stream=raw_bytes, filetype="pdf")
    result = {}
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")  # plain text, preserving whitespace
        result[i] = text
    doc.close()
    return result
 
 
def _extract_with_pdfplumber(raw_bytes: bytes) -> dict[int, str]:
    result = {}
    with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            result[i] = text
    return result
 
 
# ── Quick diagnostics ─────────────────────────────────────────────────────────
 
def diagnose(source: Union[str, Path, bytes]) -> dict:
    """
    Returns a summary dict useful for debugging extraction quality.
    Shows per-page character counts and flags thin pages.
    """
    pages = extract_pages(source)
    total_chars = sum(len(t) for t in pages.values())
    thin = [p for p, t in pages.items() if len(t.strip()) < 50]
    return {
        "total_pages": len(pages),
        "total_chars": total_chars,
        "avg_chars_per_page": total_chars // max(len(pages), 1),
        "thin_pages": thin,
        "likely_scanned": len(thin) > len(pages) * 0.5,
    }