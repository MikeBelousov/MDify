from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
import sys
import traceback

from workers.common.result import WorkerResult


Converter = Callable[[argparse.Namespace], WorkerResult]


def build_parser(worker: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=f"mdify-worker-{worker}")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--format", choices=["json"], default="json")
    parser.add_argument("--ocr", choices=["auto", "always", "off"], default="auto")
    parser.add_argument("--ocr-lang", choices=["cyrillic", "latin", "auto"], default="cyrillic")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--models-dir")
    return parser


def run(worker: str, converter: Converter) -> int:
    parser = build_parser(worker)
    args = parser.parse_args()
    args.input_path = Path(args.input)
    args.output_path = Path(args.output)

    try:
        result = converter(args)
    except Exception as error:
        traceback.print_exc(file=sys.stderr)
        result = WorkerResult.error(
            input_path=args.input,
            worker=worker,
            error_code="WORKER_INTERNAL_ERROR",
            message=str(error) or "Worker failed unexpectedly.",
        )

    print(result.to_json(), flush=True)
    return 0 if result.ok else 1
