from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def run_lite(input_path: Path, output_path: Path) -> tuple[int, dict]:
    command = [
        sys.executable,
        "-m",
        "workers.lite.mdify_worker_lite",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--format",
        "json",
    ]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    assert result.stdout.strip(), result.stderr
    return result.returncode, json.loads(result.stdout)


def test_lite_worker_converts_text_file(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.txt"
    output_path = tmp_path / "sample.md"
    input_path.write_text("Hello MDify", encoding="utf-8")

    exit_code, payload = run_lite(input_path, output_path)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["worker"] == "lite"
    assert payload["engine"] == "markitdown"
    assert payload["ocr_used"] is False
    assert "Hello MDify" in output_path.read_text(encoding="utf-8")


def test_lite_worker_rejects_unsupported_file(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.exe"
    output_path = tmp_path / "sample.md"
    input_path.write_text("nope", encoding="utf-8")

    exit_code, payload = run_lite(input_path, output_path)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_code"] == "UNSUPPORTED_FILE"
