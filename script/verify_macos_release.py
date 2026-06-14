#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import plistlib
import sys
from pathlib import Path


def verify_bundle(app: Path, variant: str) -> None:
    if variant not in {"lite", "ocr"}:
        raise ValueError(f"Unsupported variant: {variant}")
    if not app.is_dir():
        raise ValueError(f"App bundle is missing: {app}")

    contents = app / "Contents"
    with (contents / "Info.plist").open("rb") as plist:
        worker_kind = plistlib.load(plist).get("MDifyWorkerKind")
    if worker_kind != variant:
        raise ValueError(
            f"MDifyWorkerKind mismatch: expected {variant}, found {worker_kind!r}"
        )

    workers_dir = contents / "Resources" / "Workers"
    expected_name = f"mdify-worker-{variant}"
    expected_worker = workers_dir / expected_name
    if not (expected_worker / expected_name).is_file():
        raise ValueError(f"Expected worker is missing: {expected_name}")

    worker_names = {
        path.name
        for path in workers_dir.iterdir()
        if path.is_dir() and path.name.startswith("mdify-worker-")
    }
    unexpected = sorted(worker_names - {expected_name})
    if unexpected:
        raise ValueError(f"Unexpected worker in {variant} bundle: {', '.join(unexpected)}")

    internal_ocr = expected_worker / "_internal" / "workers" / "ocr"
    manifest_path = internal_ocr / "model_manifest.json"
    models_dir = internal_ocr / "models"
    if variant == "lite":
        if manifest_path.exists() or models_dir.exists():
            raise ValueError("Lite bundle unexpectedly contains OCR models")
        return

    if not manifest_path.is_file():
        raise ValueError("OCR bundle is missing model_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    model_paths = [entry.get("path") for entry in manifest.get("files", [])]
    if not model_paths or any(not isinstance(path, str) for path in model_paths):
        raise ValueError("OCR model manifest does not list valid model paths")
    missing = [path for path in model_paths if not (models_dir / path).is_file()]
    if missing:
        raise ValueError(f"OCR bundle is missing model files: {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--variant", choices=("lite", "ocr"), required=True)
    args = parser.parse_args()
    try:
        verify_bundle(args.app, args.variant)
    except (OSError, ValueError, json.JSONDecodeError, plistlib.InvalidFileException) as error:
        print(f"macOS release verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Verified {args.variant} release bundle: {args.app}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
