from __future__ import annotations

from itertools import zip_longest
import json
from pathlib import Path
from time import perf_counter

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ocr"
PRE_SMART_BASELINE_PATH = FIXTURES_DIR / "pre-smart-baseline.json"
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


def test_pre_smart_baseline_is_frozen_for_fixture_corpus() -> None:
    baseline = json.loads(PRE_SMART_BASELINE_PATH.read_text(encoding="utf-8"))

    assert baseline["source"] == "pre-smart PP-OCRv6 recognition-only"
    assert (
        baseline["captured_from_commit"]
        == "799d985e630b3efa8b88a7967bee62a568e262db"
    )
    assert {fixture["path"] for fixture in baseline["fixtures"]} == EXPECTED_FIXTURES
    assert baseline["exact_line_accuracy"] == pytest.approx(0.625)
    assert baseline["character_error_rate"] == pytest.approx(0.2752130681818182)


def test_benchmark_runs_in_macos_and_windows_ci() -> None:
    command = "pytest workers/tests/test_ocr_benchmark.py -q"

    for workflow_path in (
        Path(".github/workflows/macos-build.yml"),
        Path(".github/workflows/windows-build.yml"),
    ):
        assert command in workflow_path.read_text(encoding="utf-8")


def test_smart_ocr_meets_quality_gate() -> None:
    pytest.importorskip("onnxruntime")
    from workers.ocr.language_mode import OCRLanguageMode
    from workers.ocr.rapidocr_engine import OCRModelSet, ocr_image_to_markdown

    models_dir = Path("workers/ocr/models")
    missing_models = OCRModelSet(models_dir).missing_files()
    if missing_models:
        pytest.skip(f"OCR models are not available: {missing_models}")

    manifest = json.loads((FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8"))
    baseline = json.loads(PRE_SMART_BASELINE_PATH.read_text(encoding="utf-8"))
    fixtures = manifest["fixtures"]

    smart_results = []
    for fixture in fixtures:
        expected_lines = fixture["expected_lines"]
        started_at = perf_counter()
        smart = ocr_image_to_markdown(
            FIXTURES_DIR / fixture["path"],
            models_dir,
            OCRLanguageMode.AUTO,
        )
        elapsed_seconds = perf_counter() - started_at
        smart_lines = [line for line in smart.markdown.splitlines() if line]
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
                "line_count": smart.line_count,
                "latin_retry_count": smart.latin_retry_count,
                "latin_accept_count": smart.latin_accept_count,
                "elapsed_seconds": elapsed_seconds,
            }
        )

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
    assert 0.0 <= smart["latin_retry_ratio"] <= 1.0
    assert 0.0 <= smart["latin_accept_ratio"] <= smart["latin_retry_ratio"]
    assert smart["average_seconds_per_fixture"] > 0
    baseline_mixed = next(
        result
        for result in baseline["fixtures"]
        if result["path"] == "ru-en-mixed.png"
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
    total_lines = sum(item.get("line_count", 0) for item in results)
    return {
        "exact_line_accuracy": sum(item["exact_line_accuracy"] for item in results)
        / len(results),
        "character_error_rate": sum(item["character_error_rate"] for item in results)
        / len(results),
        "total_lines": total_lines,
        "latin_retry_count": sum(item.get("latin_retry_count", 0) for item in results),
        "latin_accept_count": sum(
            item.get("latin_accept_count", 0) for item in results
        ),
        "latin_retry_ratio": sum(
            item.get("latin_retry_count", 0) for item in results
        )
        / max(1, total_lines),
        "latin_accept_ratio": sum(
            item.get("latin_accept_count", 0) for item in results
        )
        / max(1, total_lines),
        "average_seconds_per_fixture": sum(
            item.get("elapsed_seconds", 0.0) for item in results
        )
        / len(results),
        "fixtures": results,
    }
