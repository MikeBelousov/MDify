from __future__ import annotations

import json
import argparse
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw
import pytest
from rapidocr import LangCls, LangDet, LangRec, ModelType, OCRVersion
from workers.ocr import mdify_worker_ocr, pdf_ocr, rapidocr_engine
from workers.ocr.language_mode import OCRLanguageMode, parse_language_mode
from workers.ocr.ocr_types import DetectedLine, OCRCandidate, OCRMarkdownResult
from workers.ocr.rapidocr_engine import OCRModelSet
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
        "--ocr-lang",
        OCRLanguageMode.LATIN.value,
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


def test_ocr_language_help_uses_wire_values() -> None:
    help_text = build_parser("ocr").format_help()

    assert "{auto,cyrillic,latin}" in help_text
    assert "OCRLanguageMode." not in help_text


def test_auto_language_reaches_image_ocr_boundary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    input_path = tmp_path / "scan.png"
    output_path = tmp_path / "scan.md"
    input_path.write_bytes(b"image")
    captured: list[OCRLanguageMode] = []

    def fake_ocr(
        _input_path: Path,
        _models_dir: Path,
        language_mode: OCRLanguageMode,
    ) -> OCRMarkdownResult:
        captured.append(language_mode)
        return OCRMarkdownResult("# Text\n", line_count=2, latin_retry_count=1)

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
    assert result.warnings == [
        "Smart OCR mode: auto.",
        "Retried 1 of 2 lines with latin.",
        "Retried 0 of 2 lines with PP-OCRv6.",
    ]


class FakeLineDetector:
    def __init__(self, lines: list[DetectedLine]) -> None:
        self.lines = lines
        self.calls = 0

    def detect(self, _image_path: Path) -> list[DetectedLine]:
        self.calls += 1
        return self.lines


class FakeLineRecognizer:
    def __init__(self, model: str, outputs: dict[int, tuple[str, float]]) -> None:
        self.model = model
        self.outputs = outputs
        self.calls: list[list[DetectedLine]] = []

    def recognize(self, lines: list[DetectedLine]) -> list[OCRCandidate]:
        self.calls.append(lines)
        return [
            OCRCandidate(line, *self.outputs[line.index], self.model)
            for line in lines
        ]


class FakeModelRegistry:
    def __init__(
        self,
        detector: FakeLineDetector,
        eslav: FakeLineRecognizer,
        latin: FakeLineRecognizer,
        ppocrv6: FakeLineRecognizer,
    ) -> None:
        self._detector = detector
        self._eslav = eslav
        self._latin = latin
        self._ppocrv6 = ppocrv6
        self.loads: list[str] = []

    def detector(self):
        self.loads.append("detector")
        return self._detector

    def eslav(self):
        self.loads.append("eslav")
        return self._eslav

    def latin(self):
        self.loads.append("latin")
        return self._latin

    def ppocrv6(self):
        self.loads.append("ppocrv6")
        return self._ppocrv6


def fake_line(index: int = 0) -> DetectedLine:
    return DetectedLine(
        index=index,
        box=((0, 0), (120, 0), (120, 24), (0, 24)),
        crop=np.zeros((24, 120, 3), dtype=np.uint8),
    )


def patch_fake_registry(
    monkeypatch: pytest.MonkeyPatch,
    registry: FakeModelRegistry,
) -> None:
    monkeypatch.setattr(rapidocr_engine, "get_model_registry", lambda _path: registry)
    monkeypatch.setattr(OCRModelSet, "missing_files", lambda _self, _lang=None: [])


def test_auto_pipeline_loads_only_needed_recognizers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    line = fake_line()
    registry = FakeModelRegistry(
        FakeLineDetector([line]),
        FakeLineRecognizer("eslav", {0: ("Отчёт", 0.94)}),
        FakeLineRecognizer("latin", {0: ("Otchet", 0.95)}),
        FakeLineRecognizer("ppocrv6", {0: ("Отчёт", 0.96)}),
    )
    patch_fake_registry(monkeypatch, registry)

    result = rapidocr_engine.ocr_image_to_markdown(
        tmp_path / "scan.png",
        tmp_path,
        OCRLanguageMode.AUTO,
    )

    assert result.markdown == "Отчёт"
    assert registry.loads == ["detector", "eslav"]


@pytest.mark.parametrize(
    ("mode", "expected_model"),
    [
        (OCRLanguageMode.CYRILLIC, "eslav"),
        (OCRLanguageMode.LATIN, "latin"),
    ],
)
def test_manual_pipeline_loads_only_selected_recognizer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: OCRLanguageMode,
    expected_model: str,
) -> None:
    line = fake_line()
    registry = FakeModelRegistry(
        FakeLineDetector([line]),
        FakeLineRecognizer("eslav", {0: ("Отчёт", 0.94)}),
        FakeLineRecognizer("latin", {0: ("Revenue", 0.95)}),
        FakeLineRecognizer("ppocrv6", {0: ("Unused", 0.96)}),
    )
    patch_fake_registry(monkeypatch, registry)

    rapidocr_engine.ocr_image_to_markdown(tmp_path / "scan.png", tmp_path, mode)

    assert registry.loads == ["detector", expected_model]


def test_pdf_pipeline_runs_detector_once_per_page(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    line = fake_line()
    detector = FakeLineDetector([line])
    latin = FakeLineRecognizer("latin", {0: ("Page", 0.95)})
    registry = FakeModelRegistry(
        detector,
        FakeLineRecognizer("eslav", {0: ("Страница", 0.95)}),
        latin,
        FakeLineRecognizer("ppocrv6", {0: ("Page", 0.96)}),
    )
    patch_fake_registry(monkeypatch, registry)

    class FakeBitmap:
        def to_pil(self) -> Image.Image:
            return Image.new("RGB", (200, 100), "white")

    class FakePage:
        def render(self, *, scale: float) -> FakeBitmap:
            assert scale > 0
            return FakeBitmap()

    class FakeDocument:
        def __len__(self) -> int:
            return 2

        def __getitem__(self, _index: int) -> FakePage:
            return FakePage()

    monkeypatch.setattr(pdf_ocr.pdfium, "PdfDocument", lambda _path: FakeDocument())

    result = pdf_ocr.ocr_pdf_to_markdown(
        tmp_path / "scan.pdf",
        tmp_path,
        OCRLanguageMode.LATIN,
        300,
    )

    assert detector.calls == 2
    assert len(latin.calls) == 2
    assert result.line_count == 2
    assert result.markdown == "## Page 1\n\nPage\n\n## Page 2\n\nPage\n"


def test_ocr_model_set_exposes_all_required_ppocrv5_models(tmp_path: Path) -> None:
    models = OCRModelSet(tmp_path)

    assert models.detector.name == "ch_PP-OCRv5_det_server.onnx"
    assert models.classifier.name == "ch_PP-LCNet_x0_25_textline_ori_cls_mobile.onnx"
    assert models.eslav_recognizer.name == "eslav_PP-OCRv5_rec_mobile.onnx"
    assert models.latin_recognizer.name == "latin_PP-OCRv5_rec_mobile.onnx"
    assert models.ppocrv6_recognizer.name == "PP-OCRv6_medium_rec.onnx"
    assert models.required_models == (
        tmp_path / "det/ch_PP-OCRv5_det_server.onnx",
        tmp_path / "cls/ch_PP-LCNet_x0_25_textline_ori_cls_mobile.onnx",
        tmp_path / "rec/eslav_PP-OCRv5_rec_mobile.onnx",
        tmp_path / "rec/latin_PP-OCRv5_rec_mobile.onnx",
        tmp_path / "rec/PP-OCRv6_medium_rec.onnx",
        tmp_path / "dict/PP-OCRv6_medium_rec.txt",
        tmp_path / "fonts/cyrillic.ttf",
    )


@pytest.mark.parametrize(
    ("language_mode", "filename"),
    [
        (OCRLanguageMode.CYRILLIC, "eslav_PP-OCRv5_rec_mobile.onnx"),
        (OCRLanguageMode.LATIN, "latin_PP-OCRv5_rec_mobile.onnx"),
    ],
)
def test_ocr_model_set_selects_manual_recognition_model(
    tmp_path: Path,
    language_mode: OCRLanguageMode,
    filename: str,
) -> None:
    models = OCRModelSet(tmp_path)

    assert models.rec_model_for(language_mode) == tmp_path / "rec" / filename


def test_ocr_model_set_does_not_map_auto_to_cyrillic(tmp_path: Path) -> None:
    models = OCRModelSet(tmp_path)

    with pytest.raises(ValueError, match="AUTO"):
        models.rec_model_for(OCRLanguageMode.AUTO)


@pytest.mark.parametrize(
    ("language_mode", "rec_lang", "rec_filename"),
    [
        (OCRLanguageMode.CYRILLIC, LangRec.ESLAV, "eslav_PP-OCRv5_rec_mobile.onnx"),
        (OCRLanguageMode.LATIN, LangRec.LATIN, "latin_PP-OCRv5_rec_mobile.onnx"),
    ],
)
def test_build_engine_configures_ppocrv5_models(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    language_mode: OCRLanguageMode,
    rec_lang: LangRec,
    rec_filename: str,
) -> None:
    captured: dict = {}

    def fake_rapidocr(*, params: dict):
        captured.update(params)
        return object()

    monkeypatch.setattr(rapidocr_engine, "RapidOCR", fake_rapidocr)

    rapidocr_engine.build_engine(OCRModelSet(tmp_path), language_mode)

    assert captured["Det.ocr_version"] is OCRVersion.PPOCRV5
    assert captured["Det.lang_type"] is LangDet.CH
    assert captured["Det.model_type"] is ModelType.SERVER
    assert captured["Det.model_path"] == str(tmp_path / "det/ch_PP-OCRv5_det_server.onnx")
    assert captured["Cls.ocr_version"] is OCRVersion.PPOCRV5
    assert captured["Cls.lang_type"] is LangCls.CH
    assert captured["Cls.model_path"] == str(
        tmp_path / "cls/ch_PP-LCNet_x0_25_textline_ori_cls_mobile.onnx"
    )
    assert captured["Rec.ocr_version"] is OCRVersion.PPOCRV5
    assert captured["Rec.lang_type"] is rec_lang
    assert captured["Rec.model_path"] == str(tmp_path / "rec" / rec_filename)


def test_model_manifest_uses_ppocrv5_models_and_preserves_ppocrv6() -> None:
    manifest_path = Path(__file__).resolve().parents[1] / "ocr/model_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = {entry["path"]: entry for entry in manifest["files"]}
    expected_downloads = {
        "det/ch_PP-OCRv5_det_server.onnx": (
            "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.8.0/onnx/PP-OCRv5/det/ch_PP-OCRv5_det_server.onnx",
            "0f8846b1d4bba223a2a2f9d9b44022fbc22cc019051a602b41a7fda9667e4cad",
        ),
        "cls/ch_PP-LCNet_x0_25_textline_ori_cls_mobile.onnx": (
            "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.8.0/onnx/PP-OCRv5/cls/ch_PP-LCNet_x0_25_textline_ori_cls_mobile.onnx",
            "54379ae5174d026780215fc748a7f31910dee36818e63d49e17dc598ecc82df7",
        ),
        "rec/eslav_PP-OCRv5_rec_mobile.onnx": (
            "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.8.0/onnx/PP-OCRv5/rec/eslav_PP-OCRv5_rec_mobile.onnx",
            "08705d6721849b1347d26187f15a5e362c431963a2a62bfff4feac578c489aab",
        ),
        "rec/latin_PP-OCRv5_rec_mobile.onnx": (
            "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.8.0/onnx/PP-OCRv5/rec/latin_PP-OCRv5_rec_mobile.onnx",
            "b20bd37c168a570f583afbc8cd7925603890efbcdc000a59e22c269d160b5f5a",
        ),
    }

    for path, (url, sha256) in expected_downloads.items():
        assert entries[path]["url"] == url
        assert entries[path]["sha256"] == sha256

    assert {
        "det/multi_PP-OCRv3_det_mobile.onnx",
        "cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx",
        "rec/cyrillic_PP-OCRv5_rec_mobile.onnx",
    }.isdisjoint(entries)
    assert entries["rec/PP-OCRv6_medium_rec.onnx"]["distribution"] == "git-lfs"


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
    if not (models_dir / "det/ch_PP-OCRv5_det_server.onnx").is_file():
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
