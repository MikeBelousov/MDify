from __future__ import annotations

import numpy as np

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


def test_auto_accepts_strong_eslav_without_fallbacks() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Отчёт", 0.92)})
    latin = FakeRecognizer("latin", {0: ("Otchet", 0.92)})
    ppocrv6 = FakeRecognizer("ppocrv6", {0: ("Отчёт", 0.95)})
    router = AutoOCRRouter(eslav=eslav, latin=latin, ppocrv6=ppocrv6)

    result = router.recognize([line])

    assert result.lines[0].text == "Отчёт"
    assert eslav.calls == [[line]]
    assert latin.calls == []
    assert ppocrv6.calls == []


def test_auto_does_not_construct_unused_fallback_recognizers() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Отчёт", 0.92)})
    constructed: list[str] = []

    def unused(name: str):
        def build():
            constructed.append(name)
            return FakeRecognizer(name, {0: ("unused", 0.99)})

        return build

    result = AutoOCRRouter(
        eslav=lambda: eslav,
        latin=unused("latin"),
        ppocrv6=unused("ppocrv6"),
    ).recognize([line])

    assert result.lines[0].text == "Отчёт"
    assert constructed == []


def test_auto_retries_weak_eslav_with_latin() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Revenue", 0.74)})
    latin = FakeRecognizer("latin", {0: ("Revenue", 0.94)})
    ppocrv6 = FakeRecognizer("ppocrv6", {0: ("Revenue", 0.95)})
    router = AutoOCRRouter(eslav=eslav, latin=latin, ppocrv6=ppocrv6)

    result = router.recognize([line])

    assert result.lines[0].text == "Revenue"
    assert result.lines[0].model == "latin"
    assert latin.calls == [[line]]
    assert ppocrv6.calls == []


def test_close_candidates_prefer_eslav_when_eslav_text_contains_cyrillic() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Отчёт", 0.73)})
    latin = FakeRecognizer("latin", {0: ("Отчет", 0.96)})
    ppocrv6 = FakeRecognizer("ppocrv6", {0: ("Отчет", 0.75)})
    router = AutoOCRRouter(eslav=eslav, latin=latin, ppocrv6=ppocrv6)

    result = router.recognize([line])

    assert result.lines[0].model == "eslav"
    assert result.lines[0].text == "Отчёт"


def test_close_candidates_prefer_latin_for_latin_only_text_and_run_ppocrv6() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Revenve", 0.73)})
    latin = FakeRecognizer("latin", {0: ("Revenue", 0.76)})
    ppocrv6 = FakeRecognizer("ppocrv6", {0: ("Revenue", 0.78)})
    router = AutoOCRRouter(eslav=eslav, latin=latin, ppocrv6=ppocrv6)

    result = router.recognize([line])

    assert result.lines[0].model == "latin"
    assert ppocrv6.calls == [[line]]


def test_close_digits_and_punctuation_candidates_use_confidence() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("2026: 42.5%", 0.74)})
    latin = FakeRecognizer("latin", {0: ("2026: 42,5%", 0.76)})
    ppocrv6 = FakeRecognizer("ppocrv6", {0: ("2026: 42.5%", 0.78)})
    router = AutoOCRRouter(eslav=eslav, latin=latin, ppocrv6=ppocrv6)

    result = router.recognize([line])

    assert result.lines[0].model == "latin"
    assert result.lines[0].text == "2026: 42,5%"
    assert ppocrv6.calls == [[line]]


def test_quality_difference_above_tie_margin_selects_higher_score() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Отчёт", 0.70)})
    latin = FakeRecognizer("latin", {0: ("Revenue", 0.74)})
    ppocrv6 = FakeRecognizer("ppocrv6", {0: ("Отчёт", 0.75)})
    router = AutoOCRRouter(eslav=eslav, latin=latin, ppocrv6=ppocrv6)

    result = router.recognize([line])

    assert result.lines[0].model == "latin"


def test_auto_retries_only_remaining_ambiguous_lines_with_ppocrv6() -> None:
    good_line = make_line(0)
    ambiguous_line = make_line(1, top=50)
    eslav = FakeRecognizer(
        "eslav",
        {0: ("Отчёт", 0.90), 1: ("Pасходы", 0.65)},
    )
    latin = FakeRecognizer("latin", {1: ("Pасходы", 0.68)})
    ppocrv6 = FakeRecognizer("ppocrv6", {1: ("Расходы", 0.93)})
    router = AutoOCRRouter(eslav=eslav, latin=latin, ppocrv6=ppocrv6)

    result = router.recognize([good_line, ambiguous_line])

    assert latin.calls == [[ambiguous_line]]
    assert ppocrv6.calls == [[ambiguous_line]]
    assert [line.text for line in result.lines] == ["Отчёт", "Расходы"]
    assert result.latin_retry_count == 1
    assert result.ppocrv6_retry_count == 1


def test_ppocrv6_must_improve_score_by_tie_margin() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Revenve", 0.60)})
    latin = FakeRecognizer("latin", {0: ("Revenue", 0.70)})
    ppocrv6 = FakeRecognizer("ppocrv6", {0: ("Revenuе", 0.72)})
    router = AutoOCRRouter(eslav=eslav, latin=latin, ppocrv6=ppocrv6)

    result = router.recognize([line])

    assert result.lines[0].model == "latin"


def test_ppocrv6_is_selected_at_exact_improvement_margin() -> None:
    line = make_line(0)
    eslav = FakeRecognizer("eslav", {0: ("Revenve", 0.60)})
    latin = FakeRecognizer("latin", {0: ("Revenue", 0.70)})
    ppocrv6 = FakeRecognizer("ppocrv6", {0: ("Revenue!", 0.73)})
    router = AutoOCRRouter(eslav=eslav, latin=latin, ppocrv6=ppocrv6)

    result = router.recognize([line])

    assert result.lines[0].model == "ppocrv6"


def test_empty_input_does_not_load_or_call_recognizers() -> None:
    eslav = FakeRecognizer("eslav", {})
    latin = FakeRecognizer("latin", {})
    ppocrv6 = FakeRecognizer("ppocrv6", {})

    result = AutoOCRRouter(eslav=eslav, latin=latin, ppocrv6=ppocrv6).recognize([])

    assert result.lines == []
    assert eslav.calls == []
    assert latin.calls == []
    assert ppocrv6.calls == []


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
            OCRCandidate(make_line(1, top=50), "−", 0.45, "ppocrv6")
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
