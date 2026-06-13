from __future__ import annotations

from dataclasses import dataclass

import numpy as np


OCRPoint = tuple[float, float]
OCRBox = tuple[OCRPoint, ...]


@dataclass(frozen=True)
class DetectedLine:
    index: int
    box: OCRBox
    crop: np.ndarray

