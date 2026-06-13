from __future__ import annotations

from itertools import zip_longest
import json
from pathlib import Path

from PIL import Image
import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ocr"
EXPECTED_FIXTURES = {
    "ru-clean.png",
    "en-clean.png",
    "ru-en-mixed.png",
    "latin-diacritics.png",
    "low-contrast.png",
    "rotated.png",
    "digits-and-punctuation.png",
    "mixed-script-confusable.png",
}


def edit_distance(expected: str, actual: str) -> int:
    previous = list(range(len(actual) + 1))
    for expected_index, expected_character in enumerate(expected, start=1):
        current = [expected_index]
        for actual_index, actual_character in enumerate(actual, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[actual_index] + 1,
                    previous[actual_index - 1]
                    + (expected_character != actual_character),
                )
            )
        previous = current
    return previous[-1]


def exact_line_accuracy(expected_lines: list[str], actual_lines: list[str]) -> float:
    pairs = list(zip_longest(expected_lines, actual_lines))
    if not pairs:
        return 1.0
    return sum(expected == actual for expected, actual in pairs) / len(pairs)


def character_error_rate(expected_lines: list[str], actual_lines: list[str]) -> float:
    expected = "\n".join(expected_lines)
    actual = "\n".join(actual_lines)
    return edit_distance(expected, actual) / max(1, len(expected))


def test_ocr_fixture_corpus_is_complete() -> None:
    manifest = json.loads((FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8"))
    fixture_paths = {fixture["path"] for fixture in manifest["fixtures"]}

    assert fixture_paths == EXPECTED_FIXTURES
    assert all(fixture["expected_lines"] for fixture in manifest["fixtures"])
    assert all((FIXTURES_DIR / path).is_file() for path in fixture_paths)


def test_metric_examples() -> None:
    assert exact_line_accuracy(["one", "two"], ["one", "too"]) == 0.5
    assert character_error_rate(["one", "two"], ["one", "too"]) == pytest.approx(1 / 7)


def test_ocr_baseline() -> None:
    pytest.importorskip("onnxruntime")
    from workers.ocr.ppocrv6_adapter import PPOCRV6Recognizer

    models_dir = Path("workers/ocr/models")
    model_path = models_dir / "rec" / "PP-OCRv6_medium_rec.onnx"
    dictionary_path = models_dir / "dict" / "PP-OCRv6_medium_rec.txt"
    if not model_path.is_file() or not dictionary_path.is_file():
        pytest.skip("PP-OCRv6 Git LFS model is not available")

    manifest = json.loads((FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8"))
    images = []
    for fixture in manifest["fixtures"]:
        with Image.open(FIXTURES_DIR / fixture["path"]) as image:
            images.append(image.copy())
    recognized = PPOCRV6Recognizer(model_path, dictionary_path).recognize(images)
    results = []
    for fixture, (actual, confidence) in zip(
        manifest["fixtures"],
        recognized,
        strict=True,
    ):
        actual_lines = [actual] if actual else []
        expected_lines = fixture["expected_lines"]
        results.append(
            {
                "path": fixture["path"],
                "exact_line_accuracy": exact_line_accuracy(expected_lines, actual_lines),
                "character_error_rate": character_error_rate(expected_lines, actual_lines),
                "confidence": confidence,
            }
        )

    baseline = {
        "exact_line_accuracy": sum(item["exact_line_accuracy"] for item in results)
        / len(results),
        "character_error_rate": sum(item["character_error_rate"] for item in results)
        / len(results),
        "fixtures": results,
    }
    print(f"OCR baseline: {json.dumps(baseline, ensure_ascii=False, sort_keys=True)}")


def test_smart_ocr_meets_quality_gate() -> None:
    pytest.importorskip("onnxruntime")
    from workers.ocr.language_mode import OCRLanguageMode
    from workers.ocr.ppocrv6_adapter import PPOCRV6Recognizer
    from workers.ocr.rapidocr_engine import ocr_image_to_markdown

    models_dir = Path("workers/ocr/models")
    model_path = models_dir / "rec" / "PP-OCRv6_medium_rec.onnx"
    dictionary_path = models_dir / "dict" / "PP-OCRv6_medium_rec.txt"
    if not model_path.is_file() or not dictionary_path.is_file():
        pytest.skip("PP-OCRv6 Git LFS model is not available")

    manifest = json.loads((FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8"))
    fixtures = manifest["fixtures"]
    images = []
    for fixture in fixtures:
        with Image.open(FIXTURES_DIR / fixture["path"]) as image:
            images.append(image.copy())
    baseline_outputs = PPOCRV6Recognizer(model_path, dictionary_path).recognize(images)

    baseline_results = []
    smart_results = []
    for fixture, (baseline_text, _confidence) in zip(
        fixtures,
        baseline_outputs,
        strict=True,
    ):
        expected_lines = fixture["expected_lines"]
        baseline_lines = [baseline_text] if baseline_text else []
        smart = ocr_image_to_markdown(
            FIXTURES_DIR / fixture["path"],
            models_dir,
            OCRLanguageMode.AUTO,
        )
        smart_lines = [line for line in smart.markdown.splitlines() if line]
        baseline_results.append(
            {
                "path": fixture["path"],
                "exact_line_accuracy": exact_line_accuracy(
                    expected_lines,
                    baseline_lines,
                ),
                "character_error_rate": character_error_rate(
                    expected_lines,
                    baseline_lines,
                ),
            }
        )
        smart_results.append(
            {
                "path": fixture["path"],
                "exact_line_accuracy": exact_line_accuracy(
                    expected_lines,
                    smart_lines,
                ),
                "character_error_rate": character_error_rate(
                    expected_lines,
                    smart_lines,
                ),
            }
        )

    baseline = summarize_results(baseline_results)
    smart = summarize_results(smart_results)
    print(
        "Smart OCR quality: "
        + json.dumps(
            {"baseline": baseline, "smart": smart},
            ensure_ascii=False,
            sort_keys=True,
        )
    )

    assert smart["exact_line_accuracy"] >= baseline["exact_line_accuracy"]
    assert smart["character_error_rate"] <= baseline["character_error_rate"]
    baseline_mixed = next(
        result for result in baseline_results if result["path"] == "ru-en-mixed.png"
    )
    smart_mixed = next(
        result for result in smart_results if result["path"] == "ru-en-mixed.png"
    )
    assert (
        smart_mixed["exact_line_accuracy"] > baseline_mixed["exact_line_accuracy"]
        or smart_mixed["character_error_rate"]
        < baseline_mixed["character_error_rate"]
    )


def summarize_results(results: list[dict]) -> dict:
    return {
        "exact_line_accuracy": sum(item["exact_line_accuracy"] for item in results)
        / len(results),
        "character_error_rate": sum(item["character_error_rate"] for item in results)
        / len(results),
        "fixtures": results,
    }
