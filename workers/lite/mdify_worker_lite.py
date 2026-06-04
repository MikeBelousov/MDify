from __future__ import annotations

import sys

from workers.common.cli import run
from workers.common.file_type import is_lite_supported, is_pdf
from workers.common.markitdown_convert import convert_with_markitdown, write_markdown
from workers.common.pdf_detect import appears_scanned_pdf
from workers.common.result import WorkerResult


WORKER = "lite"


def convert(args) -> WorkerResult:
    input_path = args.input_path
    output_path = args.output_path

    if not input_path.is_file():
        return WorkerResult.error(
            input_path=str(input_path),
            worker=WORKER,
            error_code="UNSUPPORTED_FILE",
            message="Input file does not exist.",
        )

    if not is_lite_supported(input_path):
        return WorkerResult.error(
            input_path=str(input_path),
            worker=WORKER,
            error_code="UNSUPPORTED_FILE",
            message=f"Unsupported file extension: {input_path.suffix}",
        )

    if is_pdf(input_path) and appears_scanned_pdf(input_path):
        return WorkerResult.error(
            input_path=str(input_path),
            worker=WORKER,
            error_code="SCANNED_PDF_REQUIRES_OCR",
            message="This PDF appears to be scanned. MDify Lite does not support OCR.",
        )

    markdown = convert_with_markitdown(input_path)
    write_markdown(output_path, markdown)
    return WorkerResult.success(
        input_path=str(input_path),
        output_path=str(output_path),
        worker=WORKER,
        engine="markitdown",
        ocr_used=False,
    )


def main() -> int:
    return run(WORKER, convert)


if __name__ == "__main__":
    raise SystemExit(main())
