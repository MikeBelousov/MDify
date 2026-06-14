from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "script/verify_macos_release.py"


def _make_bundle(tmp_path: Path, variant: str) -> Path:
    app = tmp_path / f"MDify {variant.title()}.app"
    contents = app / "Contents"
    workers = contents / "Resources" / "Workers"
    worker = workers / f"mdify-worker-{variant}"
    worker.mkdir(parents=True)
    (worker / f"mdify-worker-{variant}").write_text("worker", encoding="utf-8")
    with (contents / "Info.plist").open("wb") as plist:
        plistlib.dump({"MDifyWorkerKind": variant}, plist)

    if variant == "ocr":
        internal = worker / "_internal" / "workers" / "ocr"
        models = internal / "models"
        model_path = models / "rec" / "model.onnx"
        model_path.parent.mkdir(parents=True)
        model_path.write_text("model", encoding="utf-8")
        (internal / "model_manifest.json").write_text(
            json.dumps({"files": [{"path": "rec/model.onnx"}]}),
            encoding="utf-8",
        )
    return app


def _verify(app: Path, variant: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFIER), "--app", str(app), "--variant", variant],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_verifier_accepts_variant_specific_bundles(tmp_path: Path) -> None:
    assert _verify(_make_bundle(tmp_path, "lite"), "lite").returncode == 0
    assert _verify(_make_bundle(tmp_path, "ocr"), "ocr").returncode == 0


def test_verifier_rejects_bundle_with_both_workers(tmp_path: Path) -> None:
    app = _make_bundle(tmp_path, "lite")
    wrong_worker = app / "Contents/Resources/Workers/mdify-worker-ocr"
    wrong_worker.mkdir()

    result = _verify(app, "lite")

    assert result.returncode != 0
    assert "unexpected worker" in result.stderr.lower()


def test_verifier_rejects_ocr_bundle_with_missing_manifest_model(tmp_path: Path) -> None:
    app = _make_bundle(tmp_path, "ocr")
    model = app / (
        "Contents/Resources/Workers/mdify-worker-ocr/_internal/"
        "workers/ocr/models/rec/model.onnx"
    )
    model.unlink()

    result = _verify(app, "ocr")

    assert result.returncode != 0
    assert "missing model" in result.stderr.lower()


def test_build_scripts_run_release_verifier() -> None:
    for relative_path in ("script/build_release.sh", "script/build_and_run.sh"):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "verify_macos_release.py" in text


def test_macos_ci_runs_release_contract_tests() -> None:
    workflow = (ROOT / ".github/workflows/macos-build.yml").read_text(encoding="utf-8")
    assert "workers/tests/test_macos_release_contract.py" in workflow
