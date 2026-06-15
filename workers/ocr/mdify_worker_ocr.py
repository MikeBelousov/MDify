from __future__ import annotations

from pathlib import Path
import sys

from workers.common.cli import run
from workers.common.file_type import is_image, is_ocr_supported, is_pdf
from workers.common.markitdown_convert import convert_with_markitdown, write_markdown
from workers.common.pdf_detect import appears_scanned_pdf
from workers.common.result import WorkerResult
from workers.ocr.image_ocr import ocr_image_file_to_markdown
from workers.ocr.language_mode import parse_language_mode
from workers.ocr.pdf_ocr import ocr_pdf_to_markdown


WORKER = "ocr"


def default_models_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "workers" / "ocr" / "models"
    return Path(__file__).resolve().parent / "models"


def convert(args) -> WorkerResult:
    input_path = args.input_path
    output_path = args.output_path
    models_dir = Path(args.models_dir) if args.models_dir else default_models_dir()
    language_mode = parse_language_mode(args.ocr_lang)

    if not input_path.is_file():
        return WorkerResult.error(
            input_path=str(input_path),
            worker=WORKER,
            error_code="UNSUPPORTED_FILE",
            message="Input file does not exist.",
        )

    if not is_ocr_supported(input_path):
        return WorkerResult.error(
            input_path=str(input_path),
            worker=WORKER,
            error_code="UNSUPPORTED_FILE",
            message=f"Unsupported file extension: {input_path.suffix}",
        )

    try:
        ocr_used = False
        warnings: list[str] = []
        if is_image(input_path):
            ocr_result = ocr_image_file_to_markdown(
                input_path,
                models_dir,
                language_mode,
            )
            markdown = ocr_result.markdown
            warnings = ocr_result.warnings(language_mode.value)
            ocr_used = True
            engine = "rapidocr"
        elif is_pdf(input_path) and args.ocr != "off" and (
            args.ocr == "always" or appears_scanned_pdf(input_path)
        ):
            ocr_result = ocr_pdf_to_markdown(
                input_path,
                models_dir,
                language_mode,
                args.dpi,
            )
            markdown = ocr_result.markdown
            warnings = ocr_result.warnings(language_mode.value)
            ocr_used = True
            engine = "rapidocr"
        else:
            markdown = convert_with_markitdown(input_path)
            engine = "markitdown"
    except FileNotFoundError as error:
        return WorkerResult.error(
            input_path=str(input_path),
            worker=WORKER,
            error_code="OCR_MODEL_MISSING",
            message=str(error),
        )

    write_markdown(output_path, markdown)
    return WorkerResult.success(
        input_path=str(input_path),
        output_path=str(output_path),
        worker=WORKER,
        engine=engine,
        ocr_used=ocr_used,
        warnings=warnings,
    )


def main() -> int:
    return run(WORKER, convert)


if __name__ == "__main__":
    raise SystemExit(main())
