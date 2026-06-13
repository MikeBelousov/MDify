from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import unicodedata

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
        eslav: LineRecognizer | Callable[[], LineRecognizer],
        latin: LineRecognizer | Callable[[], LineRecognizer],
        ppocrv6: LineRecognizer | Callable[[], LineRecognizer],
    ) -> None:
        self._eslav = eslav
        self._latin = latin
        self._ppocrv6 = ppocrv6

    def recognize(self, lines: list[DetectedLine]) -> AutoOCRResult:
        if not lines:
            return AutoOCRResult([], latin_retry_count=0, ppocrv6_retry_count=0)

        eslav_recognizer = _resolve(self._eslav)
        eslav = _candidate_map(lines, eslav_recognizer.recognize(lines), "eslav")
        selected = dict(eslav)

        latin_lines = [
            line for line in lines if eslav[line.index].quality.needs_retry
        ]
        latin = (
            _candidate_map(
                latin_lines,
                _resolve(self._latin).recognize(latin_lines),
                "latin",
            )
            if latin_lines
            else {}
        )
        for line in latin_lines:
            selected[line.index] = _select_v5_candidate(
                eslav[line.index],
                latin[line.index],
            )

        ppocrv6_lines = [
            line
            for line in latin_lines
            if selected[line.index].quality.needs_retry
            or _is_clean_close_conflict(eslav[line.index], latin[line.index])
        ]
        ppocrv6 = (
            _candidate_map(
                ppocrv6_lines,
                _resolve(self._ppocrv6).recognize(ppocrv6_lines),
                "ppocrv6",
            )
            if ppocrv6_lines
            else {}
        )
        for line in ppocrv6_lines:
            candidate = ppocrv6[line.index]
            current = selected[line.index]
            improvement = (
                candidate.quality.quality_score - current.quality.quality_score
            )
            if improvement >= CANDIDATE_TIE_MARGIN - 1e-12:
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


def _resolve(
    source: LineRecognizer | Callable[[], LineRecognizer],
) -> LineRecognizer:
    if hasattr(source, "recognize"):
        return source  # type: ignore[return-value]
    return source()


def _select_v5_candidate(
    eslav: OCRCandidate,
    latin: OCRCandidate,
) -> OCRCandidate:
    difference = latin.quality.quality_score - eslav.quality.quality_score
    if abs(difference) > CANDIDATE_TIE_MARGIN + 1e-12:
        return latin if difference > 0 else eslav

    if _contains_no_letters(eslav.text) and _contains_no_letters(latin.text):
        return latin if latin.confidence > eslav.confidence else eslav
    if _contains_cyrillic(eslav.text) or _contains_cyrillic(latin.text):
        return eslav
    if _is_latin_only(eslav.text) and _is_latin_only(latin.text):
        return latin
    return latin if difference > 0 else eslav


def _is_clean_close_conflict(
    eslav: OCRCandidate,
    latin: OCRCandidate,
) -> bool:
    difference = abs(
        latin.quality.quality_score - eslav.quality.quality_score
    )
    return (
        difference <= CANDIDATE_TIE_MARGIN + 1e-12
        and eslav.text != latin.text
        and _has_clean_text(eslav)
        and _has_clean_text(latin)
    )


def _has_clean_text(candidate: OCRCandidate) -> bool:
    text_quality_reasons = {
        "empty-text",
        "mixed-confusable-token",
        "unsupported-script",
        "replacement-or-control",
        "repetition",
    }
    return not text_quality_reasons.intersection(candidate.quality.reasons)


def _contains_cyrillic(text: str) -> bool:
    return any("CYRILLIC" in unicodedata.name(character, "") for character in text)


def _is_latin_only(text: str) -> bool:
    letters = [
        character
        for character in text
        if unicodedata.category(character).startswith("L")
    ]
    return bool(letters) and all(
        "LATIN" in unicodedata.name(character, "") for character in letters
    )


def _contains_no_letters(text: str) -> bool:
    return not any(
        unicodedata.category(character).startswith("L") for character in text
    )
