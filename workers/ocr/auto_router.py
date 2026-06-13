from __future__ import annotations

from dataclasses import dataclass

from workers.ocr.line_recognition import LineRecognizer, OCRRecognitionError
from workers.ocr.ocr_types import DetectedLine, OCRCandidate, SelectedOCRLine
from workers.ocr.text_quality import CANDIDATE_TIE_MARGIN


@dataclass(frozen=True)
class AutoOCRResult:
    lines: list[SelectedOCRLine]
    latin_retry_count: int
    ppocrv6_retry_count: int


class AutoOCRRouter:
    def __init__(
        self,
        *,
        eslav: LineRecognizer,
        latin: LineRecognizer,
        ppocrv6: LineRecognizer,
    ) -> None:
        self._eslav = eslav
        self._latin = latin
        self._ppocrv6 = ppocrv6

    def recognize(self, lines: list[DetectedLine]) -> AutoOCRResult:
        if not lines:
            return AutoOCRResult([], latin_retry_count=0, ppocrv6_retry_count=0)

        eslav = _candidate_map(lines, self._eslav.recognize(lines), "eslav")
        selected = dict(eslav)

        latin_lines = [
            line for line in lines if eslav[line.index].quality.needs_retry
        ]
        latin = (
            _candidate_map(latin_lines, self._latin.recognize(latin_lines), "latin")
            if latin_lines
            else {}
        )
        for line in latin_lines:
            candidate = latin[line.index]
            if candidate.quality.quality_score > selected[line.index].quality.quality_score:
                selected[line.index] = candidate

        ppocrv6_lines = [
            line for line in latin_lines if selected[line.index].quality.needs_retry
        ]
        ppocrv6 = (
            _candidate_map(
                ppocrv6_lines,
                self._ppocrv6.recognize(ppocrv6_lines),
                "ppocrv6",
            )
            if ppocrv6_lines
            else {}
        )
        for line in ppocrv6_lines:
            candidate = ppocrv6[line.index]
            current = selected[line.index]
            if (
                candidate.quality.quality_score
                >= current.quality.quality_score + CANDIDATE_TIE_MARGIN
            ):
                selected[line.index] = candidate

        return AutoOCRResult(
            lines=[SelectedOCRLine.from_candidate(selected[line.index]) for line in lines],
            latin_retry_count=len(latin_lines),
            ppocrv6_retry_count=len(ppocrv6_lines),
        )


def _candidate_map(
    lines: list[DetectedLine],
    candidates: list[OCRCandidate],
    model: str,
) -> dict[int, OCRCandidate]:
    expected = [line.index for line in lines]
    actual = [candidate.line.index for candidate in candidates]
    if actual != expected:
        raise OCRRecognitionError(
            f"{model} recognizer did not preserve the requested line order"
        )
    return {candidate.line.index: candidate for candidate in candidates}
