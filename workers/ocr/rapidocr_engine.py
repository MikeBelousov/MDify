from __future__ import annotations

from pathlib import Path

from rapidocr import LangCls, LangDet, LangRec, OCRVersion, RapidOCR
from workers.ocr.reading_order import markdown_from_rapidocr_output


class OCRModelSet:
    def __init__(self, root: Path, lang: str) -> None:
        self.root = root
        self.lang = "latin" if lang == "latin" else "cyrillic"

    @property
    def det_model(self) -> Path:
        return self.root / "det" / "multi_PP-OCRv3_det_mobile.onnx"

    @property
    def cls_model(self) -> Path:
        return self.root / "cls" / "ch_ppocr_mobile_v2.0_cls_mobile.onnx"

    @property
    def rec_model(self) -> Path:
        return self.root / "rec" / f"{self.lang}_PP-OCRv5_rec_mobile.onnx"

    @property
    def font(self) -> Path:
        return self.root / "fonts" / "cyrillic.ttf"

    def missing_files(self) -> list[Path]:
        return [
            path
            for path in [self.det_model, self.cls_model, self.rec_model, self.font]
            if not path.is_file()
        ]


def build_engine(models: OCRModelSet) -> RapidOCR:
    rec_lang = LangRec.LATIN if models.lang == "latin" else LangRec.CYRILLIC
    params = {
        "Global.model_root_dir": str(models.root),
        "Global.font_path": str(models.font),
        "Global.log_level": "warning",
        "Det.ocr_version": OCRVersion.PPOCRV4,
        "Det.lang_type": LangDet.MULTI,
        "Det.model_path": str(models.det_model),
        "Cls.ocr_version": OCRVersion.PPOCRV4,
        "Cls.lang_type": LangCls.CH,
        "Cls.model_path": str(models.cls_model),
        "Rec.ocr_version": OCRVersion.PPOCRV5,
        "Rec.lang_type": rec_lang,
        "Rec.model_path": str(models.rec_model),
    }
    return RapidOCR(params=params)


def ocr_image_to_markdown(image_path: Path, models_dir: Path, lang: str) -> str:
    models = OCRModelSet(models_dir, lang)
    missing = models.missing_files()
    if missing:
        missing_list = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"OCR model files missing: {missing_list}")

    output = build_engine(models)(str(image_path))
    markdown = markdown_from_rapidocr_output(output)
    if markdown:
        return markdown
    markdown = output.to_markdown() if hasattr(output, "to_markdown") else ""
    if markdown:
        return markdown
    txts = getattr(output, "txts", None) or []
    return "\n".join(str(text) for text in txts)
