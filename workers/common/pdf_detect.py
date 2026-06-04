from __future__ import annotations

from pathlib import Path

from pdfminer.high_level import extract_text


def pdf_text_sample(path: Path, *, max_pages: int = 3) -> str:
    return extract_text(str(path), maxpages=max_pages) or ""


def appears_scanned_pdf(path: Path, *, min_text_chars: int = 100, max_pages: int = 3) -> bool:
    try:
        text = pdf_text_sample(path, max_pages=max_pages)
    except Exception:
        return False
    compact = "".join(text.split())
    return len(compact) < min_text_chars
