from __future__ import annotations

import json
import argparse
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw
import pytest
from workers.ocr import mdify_worker_ocr
from workers.ocr.language_mode import OCRLanguageMode, parse_language_mode
from workers.common.cli import build_parser


def run_ocr(input_path: Path, output_path: Path, models_dir: Path) -> tuple[int, dict]:
    command = [
        sys.executable,
        "-m",
        "workers.ocr.mdify_worker_ocr",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--format",
        "json",
        "--models-dir",
        str(models_dir),
    ]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert result.stdout.strip(), result.stderr
    return result.returncode, json.loads(result.stdout)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("auto", OCRLanguageMode.AUTO),
        ("cyrillic", OCRLanguageMode.CYRILLIC),
        ("latin", OCRLanguageMode.LATIN),
    ],
)
def test_parse_language_mode(raw: str, expected: OCRLanguageMode) -> None:
    assert parse_language_mode(raw) is expected


def test_ocr_language_defaults_to_auto() -> None:
    args = build_parser("ocr").parse_args(["--input", "in.png", "--output", "out.md"])

    assert args.ocr_lang is OCRLanguageMode.AUTO


def test_auto_language_reaches_image_ocr_boundary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    input_path = tmp_path / "scan.png"
    output_path = tmp_path / "scan.md"
    input_path.write_bytes(b"image")
    captured: list[OCRLanguageMode] = []

    def fake_ocr(_input_path: Path, _models_dir: Path, language_mode: OCRLanguageMode) -> str:
        captured.append(language_mode)
        return "# Text\n"

    monkeypatch.setattr(mdify_worker_ocr, "ocr_image_file_to_markdown", fake_ocr)

    result = mdify_worker_ocr.convert(
        argparse.Namespace(
            input_path=input_path,
            output_path=output_path,
            models_dir=None,
            ocr="auto",
            ocr_lang="auto",
            dpi=300,
        )
    )

    assert result.ok is True
    assert captured == [OCRLanguageMode.AUTO]


def test_ocr_worker_reports_missing_models_for_image(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.png"
    output_path = tmp_path / "sample.md"
    models_dir = tmp_path / "missing-models"
    image = Image.new("RGB", (300, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 35), "Hello MDify", fill="black")
    image.save(input_path)

    exit_code, payload = run_ocr(input_path, output_path, models_dir)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_code"] == "OCR_MODEL_MISSING"


def test_ocr_worker_converts_image_with_bundled_models(tmp_path: Path) -> None:
    models_dir = Path("workers/ocr/models")
    if not (models_dir / "det/multi_PP-OCRv3_det_mobile.onnx").is_file():
        pytest.skip("OCR models are not downloaded")

    input_path = tmp_path / "sample.png"
    output_path = tmp_path / "sample.md"
    image = Image.new("RGB", (800, 220), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 80), "HELLO MDIFY", fill="black")
    image.save(input_path)

    exit_code, payload = run_ocr(input_path, output_path, models_dir)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["worker"] == "ocr"
    assert payload["engine"] == "rapidocr"
    assert payload["ocr_used"] is True
    assert "MDIFY" in output_path.read_text(encoding="utf-8").upper()


def test_default_models_dir_uses_pyinstaller_meipass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert mdify_worker_ocr.default_models_dir() == tmp_path / "workers/ocr/models"


def test_ocr_off_for_pdf_uses_markitdown_without_rapidocr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    input_path = tmp_path / "scan.pdf"
    output_path = tmp_path / "scan.md"
    input_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(mdify_worker_ocr, "appears_scanned_pdf", lambda _: True)
    monkeypatch.setattr(mdify_worker_ocr, "convert_with_markitdown", lambda _: "markitdown text\n")

    def fail_rapidocr(*_args, **_kwargs):
        raise AssertionError("RapidOCR should not run when --ocr off")

    monkeypatch.setattr(mdify_worker_ocr, "ocr_pdf_to_markdown", fail_rapidocr)

    result = mdify_worker_ocr.convert(
        argparse.Namespace(
            input_path=input_path,
            output_path=output_path,
            models_dir=None,
            ocr="off",
            ocr_lang="cyrillic",
            dpi=300,
        )
    )

    assert result.ok is True
    assert result.engine == "markitdown"
    assert result.ocr_used is False
    assert output_path.read_text(encoding="utf-8") == "markitdown text\n"
