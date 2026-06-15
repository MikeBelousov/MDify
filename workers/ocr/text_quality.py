from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


AUTO_CONFIDENCE_THRESHOLD = 0.75
MIN_ACCEPTABLE_QUALITY = 0.70
CANDIDATE_TIE_MARGIN = 0.03

_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
_REPEATED_LETTER_PATTERN = re.compile(r"([^\W\d_])\1{3,}", re.IGNORECASE)
_LATIN_CONFUSABLES = frozenset("AaBCcEeHhIiJjKkMmNnOoPpQqSsTtXxYy")
_CYRILLIC_CONFUSABLES = frozenset("АаВССсЕеННнІіЈјКкМмОоРрЅѕТтХхУу")
_SUPPORTED_MODELS = frozenset({"eslav", "cyrillic", "latin", "ppocrv6"})


@dataclass(frozen=True)
class TextQualityScore:
    quality_score: float
    needs_retry: bool
    reasons: tuple[str, ...]
    mixed_confusable_token_ratio: float
    unsupported_script_ratio: float
    replacement_or_control_ratio: float
    repetition_penalty: float


def score_candidate(text: str, *, confidence: float, model: str) -> TextQualityScore:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    normalized_model = model.lower()
    if normalized_model not in _SUPPORTED_MODELS:
        raise ValueError(f"unsupported OCR model: {model}")

    mixed_ratio = _mixed_confusable_token_ratio(text)
    unsupported_ratio = _unsupported_script_ratio(text, normalized_model)
    replacement_ratio = _replacement_or_control_ratio(text)
    repetition_penalty = 1.0 if _REPEATED_LETTER_PATTERN.search(text) else 0.0

    quality_score = max(
        0.0,
        min(
            1.0,
            confidence
            - 0.20 * mixed_ratio
            - 0.20 * unsupported_ratio
            - 0.30 * replacement_ratio
            - 0.10 * repetition_penalty,
        ),
    )
    if not text.strip():
        quality_score = 0.0

    reasons: list[str] = []
    if not text.strip():
        reasons.append("empty-text")
    if confidence < AUTO_CONFIDENCE_THRESHOLD:
        reasons.append("low-confidence")
    if mixed_ratio > 0.20:
        reasons.append("mixed-confusable-token")
    if unsupported_ratio > 0.15:
        reasons.append("unsupported-script")
    if replacement_ratio > 0:
        reasons.append("replacement-or-control")
    if repetition_penalty > 0:
        reasons.append("repetition")
    if quality_score < MIN_ACCEPTABLE_QUALITY:
        reasons.append("low-quality")

    return TextQualityScore(
        quality_score=quality_score,
        needs_retry=bool(reasons),
        reasons=tuple(reasons),
        mixed_confusable_token_ratio=mixed_ratio,
        unsupported_script_ratio=unsupported_ratio,
        replacement_or_control_ratio=replacement_ratio,
        repetition_penalty=repetition_penalty,
    )


def _mixed_confusable_token_ratio(text: str) -> float:
    tokens = _TOKEN_PATTERN.findall(text)
    if not tokens:
        return 0.0

    mixed_count = 0
    for token in tokens:
        scripts = {_script(character) for character in token}
        mixed_scripts = "latin" in scripts and "cyrillic" in scripts
        has_confusable_pair = (
            any(character in _LATIN_CONFUSABLES for character in token)
            and any(character in _CYRILLIC_CONFUSABLES for character in token)
        )
        if mixed_scripts and has_confusable_pair:
            mixed_count += 1
    return mixed_count / len(tokens)


def _unsupported_script_ratio(text: str, model: str) -> float:
    script_characters = []
    for character in text:
        script = _script(character)
        if script in {"latin", "cyrillic", "other-letter"}:
            script_characters.append(script)
    if not script_characters:
        return 0.0

    if model in {"eslav", "cyrillic"}:
        supported = {"latin", "cyrillic"}
    elif model == "latin":
        supported = {"latin"}
    else:
        supported = {"latin", "cyrillic", "other-letter"}

    return sum(script not in supported for script in script_characters) / len(script_characters)


def _replacement_or_control_ratio(text: str) -> float:
    if not text:
        return 0.0
    invalid_count = sum(
        character == "\uFFFD" or unicodedata.category(character) == "Cc"
        for character in text
    )
    return invalid_count / len(text)


def _script(character: str) -> str:
    name = unicodedata.name(character, "")
    if "LATIN" in name:
        return "latin"
    if "CYRILLIC" in name:
        return "cyrillic"
    if unicodedata.category(character).startswith("L"):
        return "other-letter"
    return "neutral"
