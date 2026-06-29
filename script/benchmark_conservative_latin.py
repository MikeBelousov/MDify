#!/usr/bin/env python3
"""Safely cache and score conservative Latin OCR candidates."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
from typing import Any
import unicodedata

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workers.ocr.auto_router import _needs_latin_rescue, _should_accept_latin
from workers.ocr.ocr_types import DetectedLine, OCRCandidate, SelectedOCRLine
from workers.ocr.reading_order import markdown_from_selected_lines


THRESHOLDS = (0.50, 0.45, 0.40)
CANARY_FILES = (
    "en_textbook_8.png",
    "en_textbook_8_outdoor_irregular-light_oblique.JPEG",
    "ru_slide_49.jpeg",
    "ru_slide_49_indoor_light_crease_right_shadow.JPG",
)
STRESS_FILES = (
    "en_book_3.png",
    "en_slide_36.png",
    "en_slide_36_outdoor_irregular-light_oblique_wrinkle.JPEG",
    "en_slide_34_indoor_light_right_bend-out.JPEG",
    "ru_financialreport_5.jpeg",
    "ru_book_47.jpeg",
    "ru_exampaper_41_indoor_light_wrinkle_top_shadow_hold.JPG",
    "ru_newspaper_28_outdoor_light_bend-in_oblique_blur_hold.JPG",
)
BALANCED20_FILES = (
    "en_note_33.jpg",
    "en_textbook_8.png",
    "en_book_3.png",
    "en_slide_34.png",
    "en_report_50.jpg",
    "en_textbook_8_outdoor_irregular-light_oblique.JPEG",
    "en_note_33_outdoor_underexposure_flashlight-off_top_wrinkle_blur.JPEG",
    "en_slide_36_outdoor_irregular-light_oblique_wrinkle.JPEG",
    "en_slide_34_indoor_light_right_bend-out.JPEG",
    "en_book_3_outdoor_underexposure_flashlight-off_top_wrinkle.JPEG",
    "ru_slide_49.jpeg",
    "ru_book_47.jpeg",
    "ru_financialreport_5.jpeg",
    "ru_exampaper_41.jpeg",
    "ru_academicpaper_18.jpeg",
    "ru_slide_49_indoor_light_crease_right_shadow.JPG",
    "ru_book_47_indoor_light_wrinkle_right_shadow.JPG",
    "ru_exampaper_41_indoor_light_wrinkle_top_shadow_hold.JPG",
    "ru_financialreport_5_outdoor_underexposure_flashlight-on_bend-in_crease_top_hold.JPG",
    "ru_newspaper_28_outdoor_light_bend-in_oblique_blur_hold.JPG",
)
CROP_SAMPLES = (
    ("en-color-1", "en_textbook_8.png", (152, 108, 457, 166), "Lesson 1", "en"),
    ("en-color-2", "en_slide_36.png", (83, 119, 967, 247), "The Product Rule", "en"),
    ("en-gray-1", "en_magazine_19.png", (80, 376, 207, 394), "Basel, Switzerland", "en"),
    ("en-gray-2", "en_newspaper_25.png", (803, 818, 1114, 879), "IN NEW YORK", "en"),
    ("ru-color-1", "ru_newspaper_9.jpeg", (62, 563, 592, 623), "• ОФИС-МЕНЕДЖЕР", "ru"),
    ("ru-color-2", "ru_newspaper_9.jpeg", (422, 623, 754, 666), "5/2 - от 75 000 p.", "ru"),
    ("ru-gray-1", "ru_exampaper_39.jpeg", (1161, 412, 1381, 452), "ЗНАЧЕНИЯ", "ru"),
    ("ru-gray-2", "ru_exampaper_39.jpeg", (1102, 462, 1312, 506), "1) 15 часов", "ru"),
)


def stage_files(stage: str, dataset_dir: Path | None = None) -> list[str]:
    if stage == "canary":
        return list(CANARY_FILES)
    if stage == "stress":
        return list(STRESS_FILES)
    if stage == "balanced20":
        return list(BALANCED20_FILES)
    if stage == "full":
        if dataset_dir is None:
            raise ValueError("dataset_dir is required for the full stage")
        manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
        return [item["file"] for item in manifest["files"]]
    if stage == "crops":
        return [item[0] for item in CROP_SAMPLES]
    raise ValueError(f"unsupported benchmark stage: {stage}")


def atomic_write_json(destination: Path, payload: Any) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def route_cached_page(page: dict, *, trigger_confidence: float) -> dict:
    selected: list[SelectedOCRLine] = []
    attempts = 0
    accepted = 0
    for item in sorted(page["lines"], key=lambda value: value["index"]):
        line = _cached_line(item)
        eslav = _cached_candidate(line, item["eslav"], "eslav")
        latin = _cached_candidate(line, item["latin"], "latin")
        chosen = eslav
        if _needs_latin_rescue(eslav, trigger_confidence=trigger_confidence):
            attempts += 1
            if _should_accept_latin(eslav, latin):
                chosen = latin
                accepted += 1
        selected.append(SelectedOCRLine.from_candidate(chosen))
    return {
        "text": markdown_from_selected_lines(selected),
        "attempts": attempts,
        "accepted": accepted,
    }


def eslav_page_text(page: dict) -> str:
    selected = []
    for item in sorted(page["lines"], key=lambda value: value["index"]):
        line = _cached_line(item)
        selected.append(
            SelectedOCRLine.from_candidate(
                _cached_candidate(line, item["eslav"], "eslav")
            )
        )
    return markdown_from_selected_lines(selected)


def score_cache(
    cache_dir: Path,
    *,
    trigger_confidence: float,
    files: set[str] | None = None,
) -> dict:
    page_results = []
    for path in sorted(cache_dir.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        if "lines" not in page or "ground_truth" not in page:
            continue
        if files is not None and page["file"] not in files:
            continue
        expected = page["ground_truth"]
        eslav_text = eslav_page_text(page)
        routed = route_cached_page(page, trigger_confidence=trigger_confidence)
        eslav_metrics = _text_metrics(expected, eslav_text)
        candidate_metrics = _text_metrics(expected, routed["text"])
        delta = candidate_metrics["ned"] - eslav_metrics["ned"]
        effect = "helped" if delta > 1e-12 else "harmed" if delta < -1e-12 else "neutral"
        page_results.append(
            {
                "file": page["file"],
                "language": page["language"],
                "kind": page["kind"],
                "effect": effect,
                "delta_ned": delta,
                "attempts": routed["attempts"],
                "accepted": routed["accepted"],
                "elapsed_seconds": float(page.get("elapsed_seconds", 0.0)),
                "peak_rss_mib": float(page.get("peak_rss_mib", 0.0)),
                "eslav": eslav_metrics,
                "candidate": candidate_metrics,
            }
        )
    return _summarize_pages(page_results, trigger_confidence)


def select_threshold(evaluations: dict[float, dict]) -> float | None:
    for threshold in sorted(evaluations, reverse=True):
        result = evaluations[threshold]
        if (
            passes_safety_gate(result)
            and result["helped"] >= 1
            and result["accepted"] >= 1
        ):
            return threshold
    return None


def passes_safety_gate(result: dict) -> bool:
    if result["harmed"] != 0:
        return False
    scopes = [result, *result.get("groups", {}).values()]
    for scope in scopes:
        if "candidate_ned" not in scope:
            continue
        if scope["candidate_ned"] + 1e-12 < scope["eslav_ned"]:
            return False
        if scope["candidate_cer"] > scope["eslav_cer"] + 1e-12:
            return False
    return True


def _summarize_pages(page_results: list[dict], threshold: float) -> dict:
    groups: dict[str, list[dict]] = {}
    for item in page_results:
        groups.setdefault(f"{item['language']}_{item['kind']}", []).append(item)
    summary = _aggregate(page_results)
    summary.update(
        {
            "trigger_confidence": threshold,
            "groups": {name: _aggregate(items) for name, items in groups.items()},
            "page_results": page_results,
        }
    )
    return summary


def _aggregate(items: list[dict]) -> dict:
    count = len(items)
    return {
        "pages": count,
        "helped": sum(item["effect"] == "helped" for item in items),
        "harmed": sum(item["effect"] == "harmed" for item in items),
        "neutral": sum(item["effect"] == "neutral" for item in items),
        "attempts": sum(item["attempts"] for item in items),
        "accepted": sum(item["accepted"] for item in items),
        "average_seconds_per_page": _mean(
            item.get("elapsed_seconds", 0.0) for item in items
        ),
        "peak_rss_mib": max(
            (item.get("peak_rss_mib", 0.0) for item in items),
            default=0.0,
        ),
        "eslav_ned": _mean(item["eslav"]["ned"] for item in items),
        "candidate_ned": _mean(item["candidate"]["ned"] for item in items),
        "eslav_cer": _mean(item["eslav"]["cer"] for item in items),
        "candidate_cer": _mean(item["candidate"]["cer"] for item in items),
    }


def _mean(values: Any) -> float:
    materialized = list(values)
    return sum(materialized) / len(materialized) if materialized else 0.0


def _text_metrics(expected: str, actual: str) -> dict[str, float]:
    expected_norm = _normalize_text(expected)
    actual_norm = _normalize_text(actual)
    edits = _edit_distance(expected_norm, actual_norm)
    return {
        "cer": edits / max(1, len(expected_norm)),
        "ned": 1.0 - edits / max(1, len(expected_norm), len(actual_norm)),
    }


def _normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_character in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_character in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def _cached_line(item: dict) -> DetectedLine:
    return DetectedLine(
        index=int(item["index"]),
        box=tuple((float(x), float(y)) for x, y in item["box"]),
        crop=np.empty((0, 0, 3), dtype=np.uint8),
    )


def _cached_candidate(line: DetectedLine, payload: dict, model: str) -> OCRCandidate:
    return OCRCandidate(
        line=line,
        text=str(payload["text"]),
        confidence=float(payload["confidence"]),
        model=model,
    )


def _limited_params(params: dict) -> dict:
    limited = dict(params)
    limited.update(
        {
            "EngineConfig.onnxruntime.intra_op_num_threads": 2,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            "EngineConfig.onnxruntime.enable_cpu_mem_arena": False,
        }
    )
    return limited


def _build_components(models_dir: Path):
    from workers.ocr.language_mode import OCRLanguageMode
    from workers.ocr.line_detection import LineDetector
    from workers.ocr.rapidocr_engine import (
        OCRModelSet,
        _DetectionEngine,
        _engine_params,
    )

    models = OCRModelSet(models_dir)
    detector = LineDetector(
        _DetectionEngine(
            _limited_params(_engine_params(models, OCRLanguageMode.CYRILLIC))
        )
    )
    eslav, latin = _build_recognizers(models_dir)
    return detector, eslav, latin


def _build_recognizers(models_dir: Path):
    from workers.ocr.language_mode import OCRLanguageMode
    from workers.ocr.line_recognition import RapidOCRLineRecognizer
    from workers.ocr.rapidocr_engine import (
        OCRModelSet,
        _RecognitionEngine,
        _engine_params,
    )

    models = OCRModelSet(models_dir)
    eslav = RapidOCRLineRecognizer(
        _RecognitionEngine(
            _limited_params(_engine_params(models, OCRLanguageMode.CYRILLIC))
        ),
        model="eslav",
    )
    latin = RapidOCRLineRecognizer(
        _RecognitionEngine(
            _limited_params(_engine_params(models, OCRLanguageMode.LATIN))
        ),
        model="latin",
    )
    return eslav, latin


def _recognize_chunks(recognizer: Any, lines: list[DetectedLine], chunk_size: int):
    output = []
    for start in range(0, len(lines), chunk_size):
        chunk = lines[start : start + chunk_size]
        output.extend(recognizer.recognize(chunk))
        print(f"recognized {min(start + chunk_size, len(lines))}/{len(lines)}", flush=True)
    return output


def _cache_page(args: argparse.Namespace) -> int:
    manifest = json.loads((args.dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    metadata = next(item for item in manifest["files"] if item["file"] == args.file)
    detector, eslav_recognizer, latin_recognizer = _build_components(args.models_dir)
    print("detect", flush=True)
    lines = detector.detect(args.dataset_dir / args.file)
    print(f"detected {len(lines)}", flush=True)
    eslav = _recognize_chunks(eslav_recognizer, lines, args.chunk_size)
    latin = _recognize_chunks(latin_recognizer, lines, args.chunk_size)
    eslav_by_index = {item.line.index: item for item in eslav}
    latin_by_index = {item.line.index: item for item in latin}
    ground_truth = (args.ground_truth_dir / f"{Path(args.file).stem}.txt").read_text(
        encoding="utf-8"
    )
    payload = {
        "file": args.file,
        "language": metadata["language"],
        "kind": metadata["kind"],
        "ground_truth": ground_truth,
        "lines": [
            {
                "index": line.index,
                "box": [[x, y] for x, y in line.box],
                "eslav": {
                    "text": eslav_by_index[line.index].text,
                    "confidence": eslav_by_index[line.index].confidence,
                },
                "latin": {
                    "text": latin_by_index[line.index].text,
                    "confidence": latin_by_index[line.index].confidence,
                },
            }
            for line in lines
        ],
    }
    atomic_write_json(args.output, payload)
    print("done", flush=True)
    return 0


def _cache_crop(args: argparse.Namespace) -> int:
    from PIL import Image

    sample = next(item for item in CROP_SAMPLES if item[0] == args.sample)
    sample_id, filename, box, ground_truth, language = sample
    eslav_recognizer, latin_recognizer = _build_recognizers(args.models_dir)
    rgb = np.asarray(Image.open(args.dataset_dir / filename).convert("RGB"))
    x0, y0, x1, y1 = box
    crop = np.ascontiguousarray(rgb[y0:y1, x0:x1, ::-1])
    line = DetectedLine(0, ((0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)), crop)
    eslav = eslav_recognizer.recognize([line])[0]
    latin = latin_recognizer.recognize([line])[0]
    atomic_write_json(
        args.output,
        {
            "file": sample_id,
            "language": language,
            "kind": "crop",
            "ground_truth": ground_truth,
            "lines": [
                {
                    "index": 0,
                    "box": [[x, y] for x, y in line.box],
                    "eslav": {"text": eslav.text, "confidence": eslav.confidence},
                    "latin": {"text": latin.text, "confidence": latin.confidence},
                }
            ],
        },
    )
    print("done", flush=True)
    return 0


def _rss_kib(pid: int) -> int:
    result = subprocess.run(
        ["ps", "-o", "rss=", "-p", str(pid)],
        text=True,
        capture_output=True,
        check=False,
    )
    return int(result.stdout.strip() or 0)


def _run_supervised(
    command: list[str],
    *,
    max_rss_mib: int,
    progress_timeout: int,
    page_timeout: int,
) -> tuple[float, float]:
    environment = os.environ.copy()
    environment.update(
        {
            "OMP_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "2",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=environment,
    )
    selector = selectors.DefaultSelector()
    assert process.stdout is not None
    selector.register(process.stdout, selectors.EVENT_READ)
    started = last_progress = time.monotonic()
    peak_kib = 0
    stop_reason = ""
    while process.poll() is None:
        for key, _mask in selector.select(timeout=0.5):
            line = key.fileobj.readline()
            if line:
                print(line, end="", flush=True)
                last_progress = time.monotonic()
        peak_kib = max(peak_kib, _rss_kib(process.pid))
        now = time.monotonic()
        if peak_kib > max_rss_mib * 1024:
            stop_reason = f"RSS exceeded {max_rss_mib} MiB"
        elif now - last_progress > progress_timeout:
            stop_reason = f"no progress for {progress_timeout} seconds"
        elif now - started > page_timeout:
            stop_reason = f"page exceeded {page_timeout} seconds"
        if stop_reason:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise RuntimeError(stop_reason)
    remaining = process.stdout.read()
    if remaining:
        print(remaining, end="", flush=True)
    if process.returncode != 0:
        raise RuntimeError(f"benchmark child exited with {process.returncode}")
    return peak_kib / 1024, time.monotonic() - started


def _cache_stage(args: argparse.Namespace) -> int:
    items = stage_files(args.stage, args.dataset_dir)
    for item in items:
        output = args.cache_dir / f"{item}.json"
        if args.resume and output.is_file():
            print(f"skip cached {item}")
            continue
        if args.stage == "crops":
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "_cache-crop",
                "--sample",
                item,
                "--dataset-dir",
                str(args.dataset_dir),
                "--models-dir",
                str(args.models_dir),
                "--output",
                str(output),
            ]
        else:
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "_cache-page",
                "--file",
                item,
                "--dataset-dir",
                str(args.dataset_dir),
                "--ground-truth-dir",
                str(args.ground_truth_dir),
                "--models-dir",
                str(args.models_dir),
                "--output",
                str(output),
                "--chunk-size",
                str(args.chunk_size),
            ]
        print(f"cache {item}", flush=True)
        peak, elapsed = _run_supervised(
            command,
            max_rss_mib=args.max_rss_mib,
            progress_timeout=args.progress_timeout,
            page_timeout=args.page_timeout,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        payload["peak_rss_mib"] = peak
        payload["elapsed_seconds"] = elapsed
        atomic_write_json(output, payload)
        print(f"cached {item}; peak RSS {peak:.1f} MiB", flush=True)
        time.sleep(args.cooldown_seconds)
    return 0


def _score_stage(args: argparse.Namespace) -> int:
    expected_files = set(stage_files(args.stage, args.dataset_dir))
    cached_files = {
        payload["file"]
        for path in args.cache_dir.glob("*.json")
        if "lines" in (payload := json.loads(path.read_text(encoding="utf-8")))
    }
    missing = sorted(expected_files - cached_files)
    if missing:
        raise SystemExit("missing cached benchmark pages: " + ", ".join(missing))
    evaluations = {
        threshold: score_cache(
            args.cache_dir,
            trigger_confidence=threshold,
            files=expected_files,
        )
        for threshold in THRESHOLDS
    }
    safe_thresholds = [
        threshold
        for threshold in sorted(evaluations, reverse=True)
        if passes_safety_gate(evaluations[threshold])
    ]
    selected = (
        select_threshold(evaluations)
        if args.stage == "full"
        else (safe_thresholds[0] if safe_thresholds else None)
    )
    payload = {
        "stage": args.stage,
        "evaluations": {f"{key:.2f}": value for key, value in evaluations.items()},
        "selected_threshold": selected,
        "safe_thresholds": safe_thresholds,
        "decision": "conservative-latin" if selected is not None else "eslav-only",
    }
    atomic_write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    cache = subparsers.add_parser("cache")
    cache.add_argument("--stage", choices=("crops", "canary", "stress", "balanced20", "full"), required=True)
    cache.add_argument("--dataset-dir", type=Path, required=True)
    cache.add_argument("--ground-truth-dir", type=Path)
    cache.add_argument("--models-dir", type=Path, required=True)
    cache.add_argument("--cache-dir", type=Path, required=True)
    cache.add_argument("--resume", action="store_true")
    cache.add_argument("--chunk-size", type=int, default=8)
    cache.add_argument("--max-rss-mib", type=int, default=1536)
    cache.add_argument("--progress-timeout", type=int, default=60)
    cache.add_argument("--page-timeout", type=int, default=180)
    cache.add_argument("--cooldown-seconds", type=float, default=5.0)
    score = subparsers.add_parser("score")
    score.add_argument("--stage", choices=("crops", "canary", "stress", "balanced20", "full"), required=True)
    score.add_argument("--cache-dir", type=Path, required=True)
    score.add_argument("--dataset-dir", type=Path)
    score.add_argument("--output", type=Path, required=True)

    page = subparsers.add_parser("_cache-page")
    page.add_argument("--file", required=True)
    page.add_argument("--dataset-dir", type=Path, required=True)
    page.add_argument("--ground-truth-dir", type=Path, required=True)
    page.add_argument("--models-dir", type=Path, required=True)
    page.add_argument("--output", type=Path, required=True)
    page.add_argument("--chunk-size", type=int, default=8)
    crop = subparsers.add_parser("_cache-crop")
    crop.add_argument("--sample", required=True)
    crop.add_argument("--dataset-dir", type=Path, required=True)
    crop.add_argument("--models-dir", type=Path, required=True)
    crop.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "cache":
        if args.stage != "crops" and args.ground_truth_dir is None:
            raise SystemExit("--ground-truth-dir is required for page stages")
        return _cache_stage(args)
    if args.command == "score":
        if args.stage == "full" and args.dataset_dir is None:
            raise SystemExit("--dataset-dir is required for the full score stage")
        return _score_stage(args)
    if args.command == "_cache-page":
        return _cache_page(args)
    if args.command == "_cache-crop":
        return _cache_crop(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
