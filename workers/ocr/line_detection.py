from __future__ import annotations

from typing import Any

import numpy as np
from rapidocr.main import RapidOCRError
from rapidocr.utils.process_img import map_boxes_to_original

from workers.ocr.ocr_types import DetectedLine, OCRBox


class LineDetectionError(RuntimeError):
    pass


class LineDetector:
    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def detect(self, image_content: Any) -> list[DetectedLine]:
        original = self._engine.load_img(image_content)
        image, op_record = self._engine.preprocess_img(original)
        try:
            crops, detection = self._engine.detect_and_crop(image, op_record)
        except RapidOCRError:
            return []
        raw_boxes = getattr(detection, "boxes", None)
        if raw_boxes is None:
            return []

        boxes = np.asarray(raw_boxes, dtype=np.float32).copy()
        if "preprocess" in op_record:
            original_height, original_width = original.shape[:2]
            boxes = map_boxes_to_original(
                boxes,
                op_record,
                original_height,
                original_width,
            )

        try:
            oriented_crops, _classification = self._engine.cls_and_rotate(crops)
        except RapidOCRError:
            return []
        if len(boxes) != len(oriented_crops):
            raise LineDetectionError(
                "OCR detector, cropper, and classifier returned different line counts"
            )

        return [
            DetectedLine(index=index, box=_box_tuple(box), crop=crop)
            for index, (box, crop) in enumerate(
                zip(boxes, oriented_crops, strict=True)
            )
        ]


def _box_tuple(box: np.ndarray) -> OCRBox:
    return tuple((float(point[0]), float(point[1])) for point in box)
