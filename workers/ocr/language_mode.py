from __future__ import annotations

from enum import Enum


class OCRLanguageMode(str, Enum):
    AUTO = "auto"
    CYRILLIC = "cyrillic"
    LATIN = "latin"


def parse_language_mode(raw: str | OCRLanguageMode) -> OCRLanguageMode:
    if isinstance(raw, OCRLanguageMode):
        return raw
    return OCRLanguageMode(raw)
