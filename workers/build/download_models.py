#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ocr" / "model_manifest.json"
MODELS_DIR = ROOT / "ocr" / "models"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_suffix(destination.suffix + ".download")
    with urllib.request.urlopen(url, timeout=120) as response, temp_path.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
    temp_path.replace(destination)


def ensure_file(entry: dict, *, download_missing: bool) -> bool:
    path = MODELS_DIR / entry["path"]
    expected = entry["sha256"]
    if not path.exists():
        if not download_missing:
            print(f"missing: {path}", file=sys.stderr)
            return False
        print(f"downloading: {entry['path']}")
        download(entry["url"], path)

    actual = sha256(path)
    if actual != expected:
        if not download_missing:
            print(f"sha256 mismatch for {path}", file=sys.stderr)
            print(f"expected: {expected}", file=sys.stderr)
            print(f"actual:   {actual}", file=sys.stderr)
            return False
        print(f"sha256 mismatch for {path}; re-downloading", file=sys.stderr)
        print(f"expected: {expected}", file=sys.stderr)
        print(f"actual:   {actual}", file=sys.stderr)
        download(entry["url"], path)
        actual = sha256(path)
        if actual != expected:
            print(f"sha256 mismatch for {path}", file=sys.stderr)
            print(f"expected: {expected}", file=sys.stderr)
            print(f"actual:   {actual}", file=sys.stderr)
            return False
    print(f"ok: {entry['path']}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    ok = True
    for entry in manifest["files"]:
        ok = ensure_file(entry, download_missing=not args.verify_only) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
