from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from PIL import Image

from script import benchmark_conservative_latin as benchmark


def candidate(text: str, confidence: float) -> dict:
    return {"text": text, "confidence": confidence}


def cached_page(
    name: str,
    expected: str,
    eslav: tuple[str, float],
    latin: tuple[str, float],
    *,
    language: str = "en",
    kind: str = "digital",
) -> dict:
    return {
        "file": name,
        "language": language,
        "kind": kind,
        "ground_truth": expected,
        "lines": [
            {
                "index": 0,
                "box": [[0, 0], [100, 0], [100, 20], [0, 20]],
                "eslav": candidate(*eslav),
                "latin": candidate(*latin),
            }
        ],
    }


def test_stages_are_explicit_and_do_not_expand_automatically() -> None:
    assert benchmark.stage_files("canary") == [
        "en_textbook_8.png",
        "en_textbook_8_outdoor_irregular-light_oblique.JPEG",
        "ru_slide_49.jpeg",
        "ru_slide_49_indoor_light_crease_right_shadow.JPG",
    ]
    assert len(benchmark.stage_files("stress")) == 8
    assert len(benchmark.stage_files("balanced20")) == 20


def test_route_cached_page_uses_requested_trigger_threshold() -> None:
    page = cached_page(
        "sample.png",
        "Revenue",
        ("Revenve", 0.45),
        ("Revenue", 0.99),
    )

    strict = benchmark.route_cached_page(page, trigger_confidence=0.40)
    permissive = benchmark.route_cached_page(page, trigger_confidence=0.50)

    assert strict["text"] == "Revenve"
    assert strict["attempts"] == 0
    assert permissive["text"] == "Revenue"
    assert permissive["attempts"] == 1
    assert permissive["accepted"] == 1


def test_score_reports_helped_harmed_and_group_metrics(tmp_path: Path) -> None:
    pages = [
        cached_page(
            "helped.png",
            "Revenue",
            ("Revenve", 0.30),
            ("Revenue", 0.99),
        ),
        cached_page(
            "neutral.png",
            "Отчёт",
            ("Отчёт", 0.20),
            ("Report", 0.99),
            language="ru",
        ),
    ]
    for page in pages:
        (tmp_path / f"{page['file']}.json").write_text(
            json.dumps(page, ensure_ascii=False),
            encoding="utf-8",
        )

    result = benchmark.score_cache(tmp_path, trigger_confidence=0.50)

    assert result["pages"] == 2
    assert result["helped"] == 1
    assert result["harmed"] == 0
    assert result["neutral"] == 1
    assert result["attempts"] == 1
    assert result["accepted"] == 1
    assert result["groups"]["en_digital"]["harmed"] == 0
    assert result["groups"]["ru_digital"]["harmed"] == 0


def test_select_threshold_chooses_highest_zero_harm_candidate() -> None:
    evaluations = {
        0.50: {"harmed": 1, "helped": 3, "accepted": 4},
        0.45: {"harmed": 0, "helped": 2, "accepted": 2},
        0.40: {"harmed": 0, "helped": 1, "accepted": 1},
    }

    assert benchmark.select_threshold(evaluations) == 0.45


def test_select_threshold_falls_back_to_eslav_when_none_are_safe() -> None:
    evaluations = {
        0.50: {"harmed": 1, "helped": 3, "accepted": 4},
        0.45: {"harmed": 0, "helped": 0, "accepted": 0},
        0.40: {"harmed": 0, "helped": 0, "accepted": 0},
    }

    assert benchmark.select_threshold(evaluations) is None


def test_safety_gate_checks_grouped_ned_and_cer() -> None:
    safe = {
        "harmed": 0,
        "eslav_ned": 0.8,
        "candidate_ned": 0.8,
        "eslav_cer": 0.2,
        "candidate_cer": 0.2,
        "groups": {
            "en_digital": {
                "eslav_ned": 0.8,
                "candidate_ned": 0.8,
                "eslav_cer": 0.2,
                "candidate_cer": 0.2,
            }
        },
    }

    assert benchmark.passes_safety_gate(safe)
    safe["groups"]["en_digital"]["candidate_cer"] = 0.21
    assert not benchmark.passes_safety_gate(safe)


def test_score_cache_filters_to_requested_stage_files(tmp_path: Path) -> None:
    for name in ("included.png", "other.png"):
        page = cached_page(name, "Revenue", ("Revenue", 0.99), ("Revenue", 0.99))
        (tmp_path / f"{name}.json").write_text(json.dumps(page), encoding="utf-8")

    result = benchmark.score_cache(
        tmp_path,
        trigger_confidence=0.50,
        files={"included.png"},
    )

    assert result["pages"] == 1
    assert result["page_results"][0]["file"] == "included.png"


def test_atomic_json_replaces_partial_file(tmp_path: Path) -> None:
    destination = tmp_path / "result.json"

    benchmark.atomic_write_json(destination, {"complete": True})

    assert json.loads(destination.read_text(encoding="utf-8")) == {
        "complete": True
    }
    assert not destination.with_suffix(".json.tmp").exists()


def test_crop_stage_does_not_construct_detector(tmp_path: Path, monkeypatch) -> None:
    Image.new("RGB", (1000, 300), "white").save(tmp_path / "en_textbook_8.png")
    line_result = type("Candidate", (), {"text": "Lesson 1", "confidence": 0.99})()

    class Recognizer:
        def recognize(self, _lines):
            return [line_result]

    monkeypatch.setattr(
        benchmark,
        "_build_recognizers",
        lambda _models_dir: (Recognizer(), Recognizer()),
        raising=False,
    )
    monkeypatch.setattr(
        benchmark,
        "_build_components",
        lambda _models_dir: (_ for _ in ()).throw(
            AssertionError("crop stage must not construct detector")
        ),
    )
    output = tmp_path / "crop.json"

    benchmark._cache_crop(
        Namespace(
            sample="en-color-1",
            dataset_dir=tmp_path,
            models_dir=tmp_path,
            output=output,
        )
    )

    assert json.loads(output.read_text(encoding="utf-8"))["file"] == "en-color-1"
