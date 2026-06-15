from __future__ import annotations

import re
from pathlib import Path


INSTALLER_DIR = Path("windows/installer")
WORKFLOW = Path(".github/workflows/windows-build.yml")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _setup_value(installer: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.+)$", installer, re.MULTILINE)
    assert match is not None, f"{key} is missing from installer"
    return match.group(1).strip()


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_installers_define_distinct_variant_contracts() -> None:
    lite_path = INSTALLER_DIR / "MDify-Lite.iss"
    ocr_path = INSTALLER_DIR / "MDify-OCR.iss"

    assert lite_path.is_file()
    assert ocr_path.is_file()
    assert not (INSTALLER_DIR / "MDify.iss").exists()

    lite = _read(lite_path)
    ocr = _read(ocr_path)

    assert _setup_value(lite, "AppId") != _setup_value(ocr, "AppId")
    assert _setup_value(lite, "AppName") == "MDify Lite"
    assert _setup_value(ocr, "AppName") == "MDify OCR"
    assert _setup_value(lite, "DefaultDirName") == r"{localappdata}\Programs\MDify Lite"
    assert _setup_value(ocr, "DefaultDirName") == r"{localappdata}\Programs\MDify OCR"
    assert _setup_value(lite, "MinVersion") == "10.0.26200"
    assert _setup_value(ocr, "MinVersion") == "10.0.17763"
    assert _setup_value(lite, "OutputBaseFilename") == "MDify-Windows-Lite-Setup"
    assert _setup_value(ocr, "OutputBaseFilename") == "MDify-Windows-OCR-Setup"


def test_installers_include_only_their_variant_worker() -> None:
    lite = _read(INSTALLER_DIR / "MDify-Lite.iss").lower()
    ocr = _read(INSTALLER_DIR / "MDify-OCR.iss").lower()

    assert "dist\\windows\\lite\\app" in lite
    assert "mdify-worker-lite" in lite
    assert "mdify-worker-ocr" not in lite
    assert "dist\\windows\\ocr\\app" in ocr
    assert "mdify-worker-ocr" in ocr
    assert "mdify-worker-lite" not in ocr
    assert "microsoft.windows.ai" not in ocr


def test_windows_ci_builds_checks_and_uploads_two_inno_exe_installers() -> None:
    workflow = _read(WORKFLOW)
    compact = _compact(workflow)

    assert "-p:MDifyVariant=Lite -o dist/windows/lite/app" in compact
    assert "-p:MDifyVariant=Ocr -o dist/windows/ocr/app" in compact
    assert (
        "./workers/build/build_worker_windows.ps1 -Variant lite -Python python"
        in compact
    )
    assert (
        "./workers/build/build_worker_windows.ps1 -Variant ocr -Python python"
        in compact
    )
    assert ".build/workers/win-x64/mdify-worker-lite" in workflow
    assert ".build/workers/win-x64/mdify-worker-ocr" in workflow
    assert "Verify variant publish contents" in workflow
    assert "Unexpected OCR worker found in Lite publish" in workflow
    assert "PaddleOCR models found in Lite publish" in workflow
    assert '$_.Extension -eq ".onnx"' not in workflow
    assert "workers/ocr/models" in workflow
    assert "Unexpected Lite worker found in OCR publish" in workflow
    assert "Microsoft.WindowsAppSDK reference found in OCR publish deps.json" in workflow
    assert "Microsoft.Graphics.Imaging" in workflow
    assert "windows/installer/MDify-Lite.iss" in workflow
    assert "windows/installer/MDify-OCR.iss" in workflow
    assert "dist/windows/installer/MDify-Windows-Lite-Setup.exe" in workflow
    assert "dist/windows/installer/MDify-Windows-OCR-Setup.exe" in workflow
    assert "Compress-Archive" not in workflow
    assert ".zip" not in workflow.lower()
    assert ".msix" not in workflow.lower()
