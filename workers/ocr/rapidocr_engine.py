from __future__ import annotations

from pathlib import Path

from rapidocr import LangCls, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
from workers.ocr.language_mode import OCRLanguageMode, parse_language_mode
from workers.ocr.line_detection import LineDetector
from workers.ocr.reading_order import markdown_from_rapidocr_output


class OCRModelSet:
    def __init__(self, root: Path) -> None:
        self.root = root

    @property
    def det_model(self) -> Path:
        return self.root / "det" / "ch_PP-OCRv5_det_server.onnx"

    @property
    def detector(self) -> Path:
        return self.det_model

    @property
    def cls_model(self) -> Path:
        return self.root / "cls" / "ch_PP-LCNet_x0_25_textline_ori_cls_mobile.onnx"

    @property
    def classifier(self) -> Path:
        return self.cls_model

    @property
    def eslav_rec_model(self) -> Path:
        return self.root / "rec" / "eslav_PP-OCRv5_rec_mobile.onnx"

    @property
    def eslav_recognizer(self) -> Path:
        return self.eslav_rec_model

    @property
    def latin_rec_model(self) -> Path:
        return self.root / "rec" / "latin_PP-OCRv5_rec_mobile.onnx"

    @property
    def latin_recognizer(self) -> Path:
        return self.latin_rec_model

    @property
    def ppocrv6_recognizer(self) -> Path:
        return self.root / "rec" / "PP-OCRv6_medium_rec.onnx"

    @property
    def ppocrv6_dictionary(self) -> Path:
        return self.root / "dict" / "PP-OCRv6_medium_rec.txt"

    @property
    def font(self) -> Path:
        return self.root / "fonts" / "cyrillic.ttf"

    @property
    def required_models(self) -> tuple[Path, ...]:
        return (
            self.det_model,
            self.cls_model,
            self.eslav_rec_model,
            self.latin_rec_model,
            self.ppocrv6_recognizer,
            self.ppocrv6_dictionary,
            self.font,
        )

    def rec_model_for(self, lang: str | OCRLanguageMode) -> Path:
        language_mode = parse_language_mode(lang)
        if language_mode is OCRLanguageMode.CYRILLIC:
            return self.eslav_rec_model
        if language_mode is OCRLanguageMode.LATIN:
            return self.latin_rec_model
        raise ValueError("AUTO OCR language requires the automatic language router")

    def missing_files(self) -> list[Path]:
        return [path for path in self.required_models if not path.is_file()]


def build_engine(models: OCRModelSet, lang: str | OCRLanguageMode) -> RapidOCR:
    language_mode = parse_language_mode(lang)
    rec_model = models.rec_model_for(language_mode)
    rec_lang = LangRec.LATIN if language_mode is OCRLanguageMode.LATIN else LangRec.ESLAV
    params = {
        "Global.model_root_dir": str(models.root),
        "Global.font_path": str(models.font),
        "Global.log_level": "warning",
        "Det.ocr_version": OCRVersion.PPOCRV5,
        "Det.lang_type": LangDet.CH,
        "Det.model_type": ModelType.SERVER,
        "Det.model_path": str(models.det_model),
        "Cls.ocr_version": OCRVersion.PPOCRV5,
        "Cls.lang_type": LangCls.CH,
        "Cls.model_type": ModelType.MOBILE,
        "Cls.model_path": str(models.cls_model),
        "Rec.ocr_version": OCRVersion.PPOCRV5,
        "Rec.lang_type": rec_lang,
        "Rec.model_type": ModelType.MOBILE,
        "Rec.model_path": str(rec_model),
    }
    return RapidOCR(params=params)


def build_line_detector(models: OCRModelSet) -> LineDetector:
    return LineDetector(build_engine(models, OCRLanguageMode.CYRILLIC))


def ocr_image_to_markdown(
    image_path: Path,
    models_dir: Path,
    lang: str | OCRLanguageMode,
) -> str:
    models = OCRModelSet(models_dir)
    missing = models.missing_files()
    if missing:
        missing_list = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"OCR model files missing: {missing_list}")

    output = build_engine(models, lang)(str(image_path))
    markdown = markdown_from_rapidocr_output(output)
    if markdown:
        return markdown
    markdown = output.to_markdown() if hasattr(output, "to_markdown") else ""
    if markdown:
        return markdown
    txts = getattr(output, "txts", None) or []
    return "\n".join(str(text) for text in txts)
