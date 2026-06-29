from __future__ import annotations

from collections.abc import Callable

import numpy as np
from rapidocr.main import RapidOCRError

from workers.ocr.line_detection import LineDetector
from workers.ocr.model_registry import OCRModelRegistry
from workers.ocr import rapidocr_engine
from workers.ocr.language_mode import OCRLanguageMode
from workers.ocr.rapidocr_engine import OCRModelSet


FIRST_BOX = np.array([[10, 10], [110, 10], [110, 30], [10, 30]], dtype=np.float32)
SECOND_BOX = np.array([[10, 50], [150, 50], [150, 75], [10, 75]], dtype=np.float32)


class FakeDetectionResult:
    boxes = np.array([FIRST_BOX, SECOND_BOX], dtype=np.float32)


class FakeDetectionEngine:
    def __init__(self) -> None:
        self.detector_calls = 0
        self.classifier_calls = 0

    def load_img(self, image: np.ndarray) -> np.ndarray:
        return image

    def preprocess_img(self, image: np.ndarray) -> tuple[np.ndarray, dict]:
        return image, {}

    def detect_and_crop(
        self,
        _image: np.ndarray,
        _op_record: dict,
    ) -> tuple[list[np.ndarray], FakeDetectionResult]:
        self.detector_calls += 1
        return [
            np.full((20, 100, 3), 1, dtype=np.uint8),
            np.full((25, 140, 3), 2, dtype=np.uint8),
        ], FakeDetectionResult()

    def cls_and_rotate(
        self,
        crops: list[np.ndarray],
    ) -> tuple[list[np.ndarray], object]:
        self.classifier_calls += 1
        return [np.rot90(crop, 2) for crop in crops], object()


def test_detect_lines_preserves_box_and_crop_order() -> None:
    engine = FakeDetectionEngine()

    lines = LineDetector(engine).detect(np.zeros((100, 200, 3), dtype=np.uint8))

    assert [line.index for line in lines] == [0, 1]
    assert lines[0].box == tuple(map(tuple, FIRST_BOX))
    assert lines[1].box == tuple(map(tuple, SECOND_BOX))
    assert lines[0].crop[0, 0, 0] == 1
    assert lines[1].crop[0, 0, 0] == 2


def test_detect_lines_runs_detector_and_classifier_once() -> None:
    engine = FakeDetectionEngine()

    LineDetector(engine).detect(np.zeros((100, 200, 3), dtype=np.uint8))

    assert engine.detector_calls == 1
    assert engine.classifier_calls == 1


def test_detect_lines_returns_empty_without_running_classifier() -> None:
    engine = FakeDetectionEngine()

    def detect_empty(_image: np.ndarray, _op_record: dict):
        engine.detector_calls += 1
        result = FakeDetectionResult()
        result.boxes = None
        return [], result

    engine.detect_and_crop = detect_empty  # type: ignore[method-assign]

    assert LineDetector(engine).detect(np.zeros((100, 200, 3), dtype=np.uint8)) == []
    assert engine.detector_calls == 1
    assert engine.classifier_calls == 0


def test_detect_lines_returns_empty_when_classifier_has_no_output() -> None:
    engine = FakeDetectionEngine()

    def classify_empty(_crops: list[np.ndarray]):
        engine.classifier_calls += 1
        raise RapidOCRError("empty classifier")

    engine.cls_and_rotate = classify_empty  # type: ignore[method-assign]

    assert LineDetector(engine).detect(np.zeros((100, 200, 3), dtype=np.uint8)) == []
    assert engine.detector_calls == 1
    assert engine.classifier_calls == 1


def test_model_registry_builds_each_model_at_most_once() -> None:
    calls: dict[str, int] = {}

    def factory(name: str) -> Callable[[], object]:
        def build() -> object:
            calls[name] = calls.get(name, 0) + 1
            return object()

        return build

    registry = OCRModelRegistry(
        detector_factory=factory("detector"),
        eslav_factory=factory("eslav"),
        latin_factory=factory("latin"),
    )

    assert registry.detector() is registry.detector()
    assert registry.eslav() is registry.eslav()
    assert registry.latin() is registry.latin()
    assert calls == {"detector": 1, "eslav": 1, "latin": 1}


def test_stage_builders_do_not_initialize_unneeded_models(
    monkeypatch,
    tmp_path,
) -> None:
    calls: list[str] = []

    class FakeDetector:
        def __init__(self, _cfg) -> None:
            calls.append("detector")

    class FakeClassifier:
        def __init__(self, _cfg) -> None:
            calls.append("classifier")

    class FakeRecognizer:
        def __init__(self, _cfg) -> None:
            calls.append("recognizer")

    monkeypatch.setattr(rapidocr_engine, "TextDetector", FakeDetector)
    monkeypatch.setattr(rapidocr_engine, "TextClassifier", FakeClassifier)
    monkeypatch.setattr(rapidocr_engine, "TextRecognizer", FakeRecognizer)

    detector = rapidocr_engine.build_line_detector(OCRModelSet(tmp_path))

    assert calls == ["detector", "classifier"]
    assert not hasattr(detector._engine, "text_rec")

    calls.clear()
    recognizer = rapidocr_engine.build_line_recognizer(
        OCRModelSet(tmp_path),
        OCRLanguageMode.LATIN,
    )

    assert calls == ["recognizer"]
    assert not hasattr(recognizer._engine, "text_det")
    assert not hasattr(recognizer._engine, "text_cls")


def test_process_registry_reuses_one_registry_per_models_root(tmp_path) -> None:
    rapidocr_engine._registry_for_root.cache_clear()

    first = rapidocr_engine.get_model_registry(tmp_path)
    second = rapidocr_engine.get_model_registry(tmp_path / ".")

    assert first is second
