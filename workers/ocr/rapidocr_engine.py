from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from rapidocr import LangCls, LangDet, LangRec, ModelType, OCRVersion, RapidOCR
from rapidocr.ch_ppocr_cls import TextClassifier
from rapidocr.ch_ppocr_det import TextDetector
from rapidocr.ch_ppocr_rec import TextRecognizer
from rapidocr.utils.load_image import LoadImage
from workers.ocr.language_mode import OCRLanguageMode, parse_language_mode
from workers.ocr.line_detection import LineDetector
from workers.ocr.line_recognition import PPOCRV6LineRecognizer, RapidOCRLineRecognizer
from workers.ocr.model_registry import OCRModelRegistry
from workers.ocr.ppocrv6_adapter import PPOCRV6Recognizer
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

    def required_models_for(
        self,
        lang: str | OCRLanguageMode,
    ) -> tuple[Path, ...]:
        language_mode = parse_language_mode(lang)
        common = (self.detector, self.classifier, self.font)
        if language_mode is OCRLanguageMode.CYRILLIC:
            return common + (self.eslav_recognizer,)
        if language_mode is OCRLanguageMode.LATIN:
            return common + (self.latin_recognizer,)
        return self.required_models

    def missing_files(
        self,
        lang: str | OCRLanguageMode | None = None,
    ) -> list[Path]:
        required = self.required_models if lang is None else self.required_models_for(lang)
        return [path for path in required if not path.is_file()]


def build_engine(models: OCRModelSet, lang: str | OCRLanguageMode) -> RapidOCR:
    language_mode = parse_language_mode(lang)
    return RapidOCR(params=_engine_params(models, language_mode))


class _DetectionEngine(RapidOCR):
    def __init__(self, params: dict[str, Any]) -> None:
        cfg = self._load_config(None, params)
        self.min_height = cfg.Global.min_height
        self.width_height_ratio = cfg.Global.width_height_ratio
        self.max_side_len = cfg.Global.max_side_len
        self.min_side_len = cfg.Global.min_side_len

        cfg.Det.engine_cfg = cfg.EngineConfig[cfg.Det.engine_type.value]
        cfg.Det.model_root_dir = cfg.Global.model_root_dir
        self.text_det = TextDetector(cfg.Det)

        cfg.Cls.engine_cfg = cfg.EngineConfig[cfg.Cls.engine_type.value]
        cfg.Cls.model_root_dir = cfg.Global.model_root_dir
        self.text_cls = TextClassifier(cfg.Cls)
        self.load_img = LoadImage()


class _RecognitionEngine(RapidOCR):
    def __init__(self, params: dict[str, Any]) -> None:
        cfg = self._load_config(None, params)
        cfg.Rec.engine_cfg = cfg.EngineConfig[cfg.Rec.engine_type.value]
        cfg.Rec.font_path = cfg.Global.font_path
        cfg.Rec.model_root_dir = cfg.Global.model_root_dir
        self.text_rec = TextRecognizer(cfg.Rec)
        self.return_word_box = False


def _engine_params(
    models: OCRModelSet,
    lang: OCRLanguageMode,
) -> dict[str, Any]:
    rec_model = models.rec_model_for(lang)
    rec_lang = LangRec.LATIN if lang is OCRLanguageMode.LATIN else LangRec.ESLAV
    return {
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


def build_line_detector(models: OCRModelSet) -> LineDetector:
    params = _engine_params(models, OCRLanguageMode.CYRILLIC)
    return LineDetector(_DetectionEngine(params))


def build_line_recognizer(
    models: OCRModelSet,
    lang: OCRLanguageMode,
) -> RapidOCRLineRecognizer:
    if lang is OCRLanguageMode.AUTO:
        raise ValueError("AUTO OCR language requires the automatic language router")
    model = "latin" if lang is OCRLanguageMode.LATIN else "eslav"
    return RapidOCRLineRecognizer(
        _RecognitionEngine(_engine_params(models, lang)),
        model=model,
    )


def get_model_registry(models_dir: Path | str) -> OCRModelRegistry:
    return _registry_for_root(Path(models_dir).resolve())


@lru_cache(maxsize=None)
def _registry_for_root(root: Path) -> OCRModelRegistry:
    models = OCRModelSet(root)
    return OCRModelRegistry(
        detector_factory=lambda: build_line_detector(models),
        eslav_factory=lambda: build_line_recognizer(models, OCRLanguageMode.CYRILLIC),
        latin_factory=lambda: build_line_recognizer(models, OCRLanguageMode.LATIN),
        ppocrv6_factory=lambda: PPOCRV6LineRecognizer(
            PPOCRV6Recognizer(models.ppocrv6_recognizer, models.ppocrv6_dictionary)
        ),
    )


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
