from __future__ import annotations

import pytest

from workers.ocr.text_quality import (
    AUTO_CONFIDENCE_THRESHOLD,
    CANDIDATE_TIE_MARGIN,
    EMPTY_ESLAV_ACCEPT_CONFIDENCE,
    LATIN_ACCEPT_CONFIDENCE,
    LATIN_MIN_QUALITY_GAIN,
    LATIN_MIN_SIMILARITY,
    LATIN_MIN_SOURCE_LENGTH,
    LATIN_TRIGGER_CONFIDENCE,
    MIN_ACCEPTABLE_QUALITY,
    score_candidate,
)


def test_exports_stable_auto_routing_thresholds() -> None:
    assert AUTO_CONFIDENCE_THRESHOLD == 0.75
    assert MIN_ACCEPTABLE_QUALITY == 0.70
    assert CANDIDATE_TIE_MARGIN == 0.03
    assert LATIN_TRIGGER_CONFIDENCE == 0.50
    assert LATIN_ACCEPT_CONFIDENCE == 0.90
    assert EMPTY_ESLAV_ACCEPT_CONFIDENCE == 0.85
    assert LATIN_MIN_QUALITY_GAIN == 0.20
    assert LATIN_MIN_SIMILARITY == 0.70
    assert LATIN_MIN_SOURCE_LENGTH == 5


def test_clean_cyrillic_candidate_is_not_suspicious() -> None:
    result = score_candidate("Отчёт за 2026 год", confidence=0.82, model="eslav")

    assert result.quality_score >= 0.75
    assert not result.needs_retry
    assert result.reasons == ()


def test_low_confidence_candidate_needs_retry() -> None:
    result = score_candidate("Revenue", confidence=0.74, model="eslav")

    assert result.needs_retry
    assert "low-confidence" in result.reasons


@pytest.mark.parametrize("text", ["", "   \n"])
def test_empty_candidate_needs_retry_even_with_high_confidence(text: str) -> None:
    result = score_candidate(text, confidence=0.99, model="eslav")

    assert result.needs_retry
    assert result.quality_score == 0.0
    assert "empty-text" in result.reasons


def test_mixed_confusable_token_needs_retry_even_with_high_confidence() -> None:
    result = score_candidate("Pасходы", confidence=0.93, model="eslav")

    assert result.needs_retry
    assert "mixed-confusable-token" in result.reasons


def test_mixed_non_confusable_token_is_not_penalized() -> None:
    result = score_candidate("abcЖ", confidence=0.93, model="eslav")

    assert "mixed-confusable-token" not in result.reasons


@pytest.mark.parametrize("text", ["IА", "AІ"])
def test_additional_unicode_homoglyph_pairs_need_retry(text: str) -> None:
    result = score_candidate(text, confidence=0.93, model="eslav")

    assert "mixed-confusable-token" in result.reasons


def test_digits_only_candidate_uses_confidence_without_script_penalty() -> None:
    result = score_candidate("2026-06-13", confidence=0.88, model="latin")

    assert result.quality_score == pytest.approx(0.88)
    assert not result.needs_retry


def test_latin_model_retries_cyrillic_candidate() -> None:
    result = score_candidate("Доход", confidence=0.95, model="latin")

    assert result.needs_retry
    assert "unsupported-script" in result.reasons


def test_replacement_and_control_characters_force_retry() -> None:
    result = score_candidate("Reve\uFFFDnue\u0007", confidence=0.99, model="latin")

    assert result.needs_retry
    assert "replacement-or-control" in result.reasons


def test_unicode_format_character_is_not_treated_as_control() -> None:
    result = score_candidate("Revenue\u200D", confidence=0.99, model="latin")

    assert "replacement-or-control" not in result.reasons


def test_repeated_character_run_is_penalized() -> None:
    result = score_candidate("Totaallllll", confidence=0.96, model="latin")

    assert result.needs_retry
    assert "repetition" in result.reasons


@pytest.mark.parametrize("text", ["0000", "----", "!!!!"])
def test_repeated_digits_and_punctuation_are_not_penalized(text: str) -> None:
    result = score_candidate(text, confidence=0.96, model="latin")

    assert "repetition" not in result.reasons


def test_unknown_model_is_rejected() -> None:
    with pytest.raises(ValueError, match="model"):
        score_candidate("Revenue", confidence=0.9, model="latni")


def test_rejects_confidence_outside_probability_range() -> None:
    with pytest.raises(ValueError, match="confidence"):
        score_candidate("Revenue", confidence=1.2, model="latin")
