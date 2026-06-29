from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from workers.ocr.text_quality import TextQualityScore, score_candidate


OCRPoint = tuple[float, float]
OCRBox = tuple[OCRPoint, ...]


@dataclass(frozen=True)
class DetectedLine:
    index: int
    box: OCRBox
    crop: np.ndarray


@dataclass(frozen=True)
class OCRCandidate:
    line: DetectedLine
    text: str
    confidence: float
    model: str

    @property
    def quality(self) -> TextQualityScore:
        return score_candidate(
            self.text,
            confidence=self.confidence,
            model=self.model,
        )


@dataclass(frozen=True)
class SelectedOCRLine:
    index: int
    box: OCRBox
    text: str
    confidence: float
    model: str
    quality: TextQualityScore

    @classmethod
    def from_candidate(cls, candidate: OCRCandidate) -> "SelectedOCRLine":
        return cls(
            index=candidate.line.index,
            box=candidate.line.box,
            text=candidate.text,
            confidence=candidate.confidence,
            model=candidate.model,
            quality=candidate.quality,
        )


@dataclass(frozen=True)
class OCRMarkdownResult:
    markdown: str
    line_count: int = 0
    latin_retry_count: int = 0
    ppocrv6_retry_count: int = 0
    latin_accept_count: int = 0

    def warnings(self, mode: str) -> list[str]:
        warnings = [f"Smart OCR mode: {mode}."]
        if mode == "auto":
            warnings.extend(
                [
                    (
                        f"Retried {self.latin_retry_count} of {self.line_count} "
                        "lines with latin."
                    ),
                    f"Accepted {self.latin_accept_count} latin replacement"
                    + ("." if self.latin_accept_count == 1 else "s."),
                ]
            )
        return warnings
