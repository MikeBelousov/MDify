from __future__ import annotations

from pathlib import Path
import tempfile

from workers.common.markdown_postprocess import normalize_markdown
from workers.ocr.image_preprocess import prepare_image_for_ocr
from workers.ocr.rapidocr_engine import ocr_image_to_markdown


def ocr_image_file_to_markdown(input_path: Path, models_dir: Path, lang: str) -> str:
    with tempfile.TemporaryDirectory(prefix="mdify-ocr-image-") as temp_dir:
        prepared_path = prepare_image_for_ocr(input_path, Path(temp_dir))
        return normalize_markdown(ocr_image_to_markdown(prepared_path, models_dir, lang))
