from __future__ import annotations

from pathlib import Path


def test_windows_worker_build_script_declares_expected_contract() -> None:
    script = Path("workers/build/build_worker_windows.ps1")

    text = script.read_text(encoding="utf-8")

    assert '[ValidateSet("lite", "ocr")]' in text
    assert '[string]$Variant = "lite"' in text
    assert '[string]$Python = "python"' in text
    assert '[string]$DistDir = ".build/workers/win-x64"' in text
    assert "--onedir" in text
    assert "--collect-all" in text
    assert "markitdown" in text
    assert "magika" in text
    assert "rapidocr" in text
    assert "onnxruntime" in text
    assert "cv2" in text
    assert "pypdfium2" in text
    assert "PIL" in text
    assert "workers/ocr/model_manifest.json" in text
    assert "workers/ocr/models" in text
