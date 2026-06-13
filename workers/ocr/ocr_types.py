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

