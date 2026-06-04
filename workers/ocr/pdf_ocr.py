from __future__ import annotations

from pathlib import Path
import tempfile

import pypdfium2 as pdfium

from workers.common.markdown_postprocess import normalize_markdown
from workers.ocr.image_preprocess import prepare_image_for_ocr
from workers.ocr.rapidocr_engine import ocr_image_to_markdown


def ocr_pdf_to_markdown(input_path: Path, models_dir: Path, lang: str, dpi: int) -> str:
    scale = dpi / 72.0
    document = pdfium.PdfDocument(str(input_path))
    parts: list[str] = []

    with tempfile.TemporaryDirectory(prefix="mdify-ocr-pages-") as temp_dir:
        temp_path = Path(temp_dir)
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=scale)
            image_path = temp_path / f"page-{index + 1}.png"
            bitmap.to_pil().save(image_path)
            prepared_path = prepare_image_for_ocr(image_path, temp_path)
            page_markdown = ocr_image_to_markdown(prepared_path, models_dir, lang)
            if page_markdown.strip():
                parts.append(f"## Page {index + 1}\n\n{page_markdown.strip()}")

    return normalize_markdown("\n\n".join(parts))
