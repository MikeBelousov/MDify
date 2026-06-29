from __future__ import annotations

from typing import Any, Protocol, Sequence

from workers.ocr.ocr_types import DetectedLine, OCRCandidate


class OCRRecognitionError(RuntimeError):
    pass


class LineRecognizer(Protocol):
    def recognize(self, lines: list[DetectedLine]) -> list[OCRCandidate]: ...


class RapidOCRLineRecognizer:
    def __init__(self, engine: Any, *, model: str) -> None:
        self._engine = engine
        self._model = model

    def recognize(self, lines: list[DetectedLine]) -> list[OCRCandidate]:
        if not lines:
            return []

        output = self._engine.recognize_txt([line.crop for line in lines])
        texts = _required_sequence(output, "txts")
        scores = _required_sequence(output, "scores")
        _validate_output_count(lines, texts, scores, self._model)
        return [
            OCRCandidate(
                line=line,
                text=str(text),
                confidence=float(score),
                model=self._model,
            )
            for line, text, score in zip(lines, texts, scores, strict=True)
        ]


def _required_sequence(output: Any, name: str) -> Sequence[Any]:
    value = getattr(output, name, None)
    if value is None:
        raise OCRRecognitionError(f"OCR recognizer returned no {name}")
    return value


def _validate_output_count(
    lines: list[DetectedLine],
    texts: Sequence[Any],
    scores: Sequence[Any],
    model: str,
) -> None:
    if len(texts) != len(lines) or len(scores) != len(lines):
        raise OCRRecognitionError(
            f"{model} returned a different result count than the input lines"
        )
