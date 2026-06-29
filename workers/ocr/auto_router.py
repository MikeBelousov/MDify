from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re
import unicodedata

from workers.ocr.line_recognition import LineRecognizer, OCRRecognitionError
from workers.ocr.ocr_types import DetectedLine, OCRCandidate, SelectedOCRLine
from workers.ocr.text_quality import (
    EMPTY_ESLAV_ACCEPT_CONFIDENCE,
    LATIN_ACCEPT_CONFIDENCE,
    LATIN_MIN_QUALITY_GAIN,
    LATIN_MIN_SIMILARITY,
    LATIN_MIN_SOURCE_LENGTH,
    LATIN_TRIGGER_CONFIDENCE,
)


_SEVERE_ESLAV_REASONS = frozenset({"replacement-or-control", "repetition"})
_STRUCTURAL_REJECTION_REASONS = frozenset(
    {
        "empty-text",
        "mixed-confusable-token",
        "unsupported-script",
        "replacement-or-control",
        "repetition",
    }
)


@dataclass(frozen=True)
class AutoOCRResult:
    lines: list[SelectedOCRLine]
    latin_retry_count: int = 0
    ppocrv6_retry_count: int = 0
    latin_accept_count: int = 0


class AutoOCRRouter:
    def __init__(
        self,
        *,
        eslav: LineRecognizer | Callable[[], LineRecognizer],
        latin: LineRecognizer | Callable[[], LineRecognizer],
    ) -> None:
        self._eslav = eslav
        self._latin = latin

    def recognize(self, lines: list[DetectedLine]) -> AutoOCRResult:
        if not lines:
            return AutoOCRResult([])

        eslav = _candidate_map(
            lines,
            _resolve(self._eslav).recognize(lines),
            "eslav",
        )
        selected = dict(eslav)
        latin_lines = [
            line
            for line in lines
            if _needs_latin_rescue(eslav[line.index])
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

        latin_accept_count = 0
        for line in latin_lines:
            if _should_accept_latin(eslav[line.index], latin[line.index]):
                selected[line.index] = latin[line.index]
                latin_accept_count += 1

        return AutoOCRResult(
            lines=[
                SelectedOCRLine.from_candidate(selected[line.index])
                for line in lines
            ],
            latin_retry_count=len(latin_lines),
            latin_accept_count=latin_accept_count,
            ppocrv6_retry_count=0,
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


def _needs_latin_rescue(
    candidate: OCRCandidate,
    *,
    trigger_confidence: float = LATIN_TRIGGER_CONFIDENCE,
) -> bool:
    text = candidate.text.strip()
    if not text:
        return True
    if _contains_cyrillic(text) or not _is_latin_only(text):
        return False
    return (
        candidate.confidence < trigger_confidence
        or bool(_SEVERE_ESLAV_REASONS.intersection(candidate.quality.reasons))
    )


def _should_accept_latin(
    eslav: OCRCandidate,
    latin: OCRCandidate,
) -> bool:
    if not _is_latin_only(latin.text):
        return False
    if _STRUCTURAL_REJECTION_REASONS.intersection(latin.quality.reasons):
        return False

    normalized_eslav = _normalize_for_similarity(eslav.text)
    if not normalized_eslav:
        return (
            latin.confidence >= EMPTY_ESLAV_ACCEPT_CONFIDENCE
            and latin.quality.quality_score >= EMPTY_ESLAV_ACCEPT_CONFIDENCE
        )

    if len(normalized_eslav) < LATIN_MIN_SOURCE_LENGTH:
        return False
    if latin.confidence < LATIN_ACCEPT_CONFIDENCE:
        return False
    quality_gain = latin.quality.quality_score - eslav.quality.quality_score
    if quality_gain + 1e-12 < LATIN_MIN_QUALITY_GAIN:
        return False
    return _normalized_similarity(eslav.text, latin.text) >= LATIN_MIN_SIMILARITY


def _normalized_similarity(left: str, right: str) -> float:
    normalized_left = _normalize_for_similarity(left)
    normalized_right = _normalize_for_similarity(right)
    max_length = max(len(normalized_left), len(normalized_right))
    if max_length == 0:
        return 1.0
    return 1.0 - _edit_distance(normalized_left, normalized_right) / max_length


def _normalize_for_similarity(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def _edit_distance(left: str, right: str) -> int:
    if len(left) > len(right):
        left, right = right, left
    previous = list(range(len(left) + 1))
    for right_index, right_character in enumerate(right, start=1):
        current = [right_index]
        for left_index, left_character in enumerate(left, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[left_index] + 1,
                    previous[left_index - 1]
                    + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


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
