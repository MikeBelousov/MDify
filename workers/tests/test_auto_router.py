from __future__ import annotations

import numpy as np

from workers.ocr import auto_router
from workers.ocr.auto_router import AutoOCRRouter
from workers.ocr.line_recognition import RapidOCRLineRecognizer
from workers.ocr.ocr_types import DetectedLine, OCRCandidate, SelectedOCRLine
from workers.ocr.reading_order import markdown_from_selected_lines


def make_line(index: int, *, top: float = 10) -> DetectedLine:
    return DetectedLine(
        index=index,
        box=((10, top), (110, top), (110, top + 20), (10, top + 20)),
        crop=np.zeros((20, 100, 3), dtype=np.uint8),
    )


class FakeRecognizer:
    def __init__(self, model: str, outputs: dict[int, tuple[str, float]]) -> None:
        self.model = model
        self.outputs = outputs
        self.calls: list[list[DetectedLine]] = []

    def recognize(self, lines: list[DetectedLine]) -> list[OCRCandidate]:
        self.calls.append(lines)
        return [
            OCRCandidate(
                line=line,
                text=self.outputs[line.index][0],
                confidence=self.outputs[line.index][1],
                model=self.model,
            )
            for line in lines
        ]


def test_strong_eslav_does_not_construct_latin() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Revenue", 0.92)})

    def fail_latin() -> FakeRecognizer:
        raise AssertionError("strong Eslavic result must not construct Latin")

    result = AutoOCRRouter(eslav=eslav, latin=fail_latin).recognize([line])

    assert result.lines[0].text == "Revenue"
    assert result.latin_retry_count == 0
    assert result.latin_accept_count == 0
    assert result.ppocrv6_retry_count == 0


def test_weak_cyrillic_eslav_does_not_run_latin() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Отчёт", 0.20)})
    latin = FakeRecognizer("latin", {0: ("Report", 0.99)})

    result = AutoOCRRouter(eslav=eslav, latin=latin).recognize([line])

    assert result.lines[0].text == "Отчёт"
    assert latin.calls == []


def test_digits_and_punctuation_do_not_run_latin() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("2026: 42.5%", 0.20)})
    latin = FakeRecognizer("latin", {0: ("2026: 425%", 0.99)})

    result = AutoOCRRouter(eslav=eslav, latin=latin).recognize([line])

    assert result.lines[0].text == "2026: 42.5%"
    assert latin.calls == []


def test_weak_english_eslav_runs_and_accepts_latin() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Revenve", 0.49)})
    latin = FakeRecognizer("latin", {0: ("Revenue", 0.95)})

    result = AutoOCRRouter(eslav=eslav, latin=latin).recognize([line])

    assert latin.calls == [[line]]
    assert result.lines[0].text == "Revenue"
    assert result.lines[0].model == "latin"
    assert result.latin_retry_count == 1
    assert result.latin_accept_count == 1


def test_latin_below_accept_confidence_is_rejected() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Revenve", 0.40)})
    latin = FakeRecognizer("latin", {0: ("Revenue", 0.89)})

    result = AutoOCRRouter(eslav=eslav, latin=latin).recognize([line])

    assert result.lines[0].text == "Revenve"
    assert result.latin_retry_count == 1
    assert result.latin_accept_count == 0


def test_latin_without_minimum_quality_gain_is_rejected() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Revenuuuu", 0.95)})
    latin = FakeRecognizer("latin", {0: ("Revenue", 0.99)})

    result = AutoOCRRouter(eslav=eslav, latin=latin).recognize([line])

    assert latin.calls == [[line]]
    assert result.lines[0].text == "Revenuuuu"
    assert result.latin_accept_count == 0


def test_dissimilar_latin_rewrite_is_rejected() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Revenve", 0.30)})
    latin = FakeRecognizer("latin", {0: ("Invoice", 0.99)})

    result = AutoOCRRouter(eslav=eslav, latin=latin).recognize([line])

    assert result.lines[0].text == "Revenve"
    assert result.latin_accept_count == 0


def test_short_nonempty_eslav_is_never_replaced() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Tota", 0.30)})
    latin = FakeRecognizer("latin", {0: ("Total", 0.99)})

    result = AutoOCRRouter(eslav=eslav, latin=latin).recognize([line])

    assert latin.calls == [[line]]
    assert result.lines[0].text == "Tota"
    assert result.latin_accept_count == 0


def test_empty_eslav_accepts_clean_latin_at_threshold() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("", 0.99)})
    latin = FakeRecognizer("latin", {0: ("Revenue", 0.85)})

    result = AutoOCRRouter(eslav=eslav, latin=latin).recognize([line])

    assert result.lines[0].text == "Revenue"
    assert result.lines[0].model == "latin"
    assert result.latin_retry_count == 1
    assert result.latin_accept_count == 1


def test_empty_eslav_rejects_latin_below_threshold() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("", 0.99)})
    latin = FakeRecognizer("latin", {0: ("Revenue", 0.849)})

    result = AutoOCRRouter(eslav=eslav, latin=latin).recognize([line])

    assert result.lines[0].text == ""
    assert result.lines[0].model == "eslav"
    assert result.latin_accept_count == 0


def test_normalized_similarity_ignores_case_and_whitespace() -> None:
    assert auto_router._normalized_similarity(
        " Revenue\n report ",
        "revenue report",
    ) == 1.0


def test_auto_preserves_input_order_and_counts_only_rescued_lines() -> None:
    lines = [make_line(0), make_line(1, top=50)]
    eslav = FakeRecognizer(
        "eslav",
        {0: ("Revenue", 0.95), 1: ("Revenve", 0.30)},
    )
    latin = FakeRecognizer("latin", {1: ("Revenue", 0.99)})

    result = AutoOCRRouter(eslav=eslav, latin=latin).recognize(lines)

    assert [item.index for item in result.lines] == [0, 1]
    assert [item.text for item in result.lines] == ["Revenue", "Revenue"]
    assert latin.calls == [[lines[1]]]
    assert result.latin_retry_count == 1
    assert result.latin_accept_count == 1


def test_empty_input_does_not_load_recognizers() -> None:
    def fail() -> FakeRecognizer:
        raise AssertionError("empty input must not construct recognizers")

    result = AutoOCRRouter(eslav=fail, latin=fail).recognize([])

    assert result.lines == []
    assert result.latin_retry_count == 0
    assert result.latin_accept_count == 0


def test_auto_result_preserves_legacy_positional_counter_order() -> None:
    result = auto_router.AutoOCRResult([], 2, 3)

    assert result.latin_retry_count == 2
    assert result.ppocrv6_retry_count == 3
    assert result.latin_accept_count == 0


def test_reading_order_accepts_selected_lines_and_preserves_blank_gaps() -> None:
    selected = [
        SelectedOCRLine.from_candidate(
            OCRCandidate(make_line(2, top=100), "below", 0.9, "latin")
        ),
        SelectedOCRLine.from_candidate(
            OCRCandidate(make_line(1, top=10), "right", 0.9, "latin")
        ),
        SelectedOCRLine.from_candidate(
            OCRCandidate(
                DetectedLine(
                    index=0,
                    box=((0, 10), (60, 10), (60, 30), (0, 30)),
                    crop=np.zeros((20, 60, 3), dtype=np.uint8),
                ),
                "left",
                0.9,
                "latin",
            )
        ),
    ]

    assert markdown_from_selected_lines(selected) == "left right\n\nbelow"


def test_reading_order_drops_low_quality_punctuation_only_hallucination() -> None:
    selected = [
        SelectedOCRLine.from_candidate(
            OCRCandidate(make_line(0), "Revenue", 0.95, "latin")
        ),
        SelectedOCRLine.from_candidate(
            OCRCandidate(make_line(1, top=50), "−", 0.45, "eslav")
        ),
    ]

    assert markdown_from_selected_lines(selected) == "Revenue"


class FakeRecOutput:
    txts = ("one", "two")
    scores = (0.91, 0.82)


class FakeRapidOCREngine:
    def __init__(self) -> None:
        self.calls: list[list[np.ndarray]] = []

    def recognize_txt(self, crops: list[np.ndarray]) -> FakeRecOutput:
        self.calls.append(crops)
        return FakeRecOutput()


def test_rapidocr_line_recognizer_uses_only_existing_crops() -> None:
    lines = [make_line(0), make_line(1)]
    engine = FakeRapidOCREngine()

    candidates = RapidOCRLineRecognizer(engine, model="latin").recognize(lines)

    assert engine.calls == [[line.crop for line in lines]]
    assert [(item.text, item.confidence, item.model) for item in candidates] == [
        ("one", 0.91, "latin"),
        ("two", 0.82, "latin"),
    ]
