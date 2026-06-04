from __future__ import annotations

from pathlib import Path

from PIL import Image

from workers.ocr.image_preprocess import prepare_image_for_ocr
from workers.ocr.reading_order import markdown_from_rapidocr_output


class FakeRapidOCROutput:
    def __init__(self, boxes: list[list[list[float]]], txts: tuple[str, ...]) -> None:
        self.boxes = boxes
        self.txts = txts


def test_reading_order_groups_lines_and_sorts_words_left_to_right() -> None:
    output = FakeRapidOCROutput(
        boxes=[
            [[220, 10], [300, 10], [300, 30], [220, 30]],
            [[20, 10], [100, 10], [100, 30], [20, 30]],
            [[20, 80], [140, 80], [140, 100], [20, 100]],
        ],
        txts=("right", "left", "below"),
    )

    assert markdown_from_rapidocr_output(output) == "left right\n\nbelow"


def test_reading_order_returns_empty_string_when_boxes_and_texts_do_not_match() -> None:
    output = FakeRapidOCROutput(
        boxes=[[[20, 10], [100, 10], [100, 30], [20, 30]]],
        txts=("one", "two"),
    )

    assert markdown_from_rapidocr_output(output) == ""


def test_prepare_image_for_ocr_flattens_alpha_and_caps_upscale(tmp_path: Path) -> None:
    input_path = tmp_path / "transparent.png"
    image = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
    image.save(input_path)

    prepared_path = prepare_image_for_ocr(input_path, tmp_path)
    prepared = Image.open(prepared_path)

    assert prepared.mode == "RGB"
    assert prepared.size == (800, 400)
    assert prepared.getpixel((10, 10)) == (255, 255, 255)


def test_prepare_image_for_ocr_applies_exif_orientation(tmp_path: Path) -> None:
    input_path = tmp_path / "rotated.jpg"
    image = Image.new("RGB", (20, 40), "white")
    exif = Image.Exif()
    exif[274] = 6
    image.save(input_path, exif=exif)

    prepared_path = prepare_image_for_ocr(input_path, tmp_path, min_long_side=0)
    prepared = Image.open(prepared_path)

    assert prepared.size == (40, 20)
