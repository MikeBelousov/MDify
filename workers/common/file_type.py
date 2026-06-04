from __future__ import annotations

from pathlib import Path


LITE_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".xls",
    ".html",
    ".htm",
    ".csv",
    ".json",
    ".xml",
    ".txt",
    ".md",
    ".zip",
    ".epub",
}

OCR_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
    ".bmp",
}

OCR_EXTENSIONS = LITE_EXTENSIONS | OCR_IMAGE_EXTENSIONS


def extension(path: Path) -> str:
    return path.suffix.lower()


def is_pdf(path: Path) -> bool:
    return extension(path) == ".pdf"


def is_image(path: Path) -> bool:
    return extension(path) in OCR_IMAGE_EXTENSIONS


def is_lite_supported(path: Path) -> bool:
    return extension(path) in LITE_EXTENSIONS


def is_ocr_supported(path: Path) -> bool:
    return extension(path) in OCR_EXTENSIONS
