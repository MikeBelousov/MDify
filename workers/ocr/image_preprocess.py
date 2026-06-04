from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


def prepare_image_for_ocr(
    input_path: Path,
    temp_dir: Path,
    *,
    min_long_side: int = 1600,
    max_scale: float = 2.0,
) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = temp_dir / f"{input_path.stem}-ocr.png"

    with Image.open(input_path) as image:
        prepared = ImageOps.exif_transpose(image)

        if prepared.mode in ("RGBA", "LA") or "transparency" in prepared.info:
            rgba = prepared.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            background.alpha_composite(rgba)
            prepared = background.convert("RGB")
        else:
            prepared = prepared.convert("RGB")

        width, height = prepared.size
        longest = max(width, height)
        if min_long_side > 0 and longest > 0 and longest < min_long_side:
            scale = min(max_scale, min_long_side / longest)
            if scale > 1.0:
                resized = (
                    max(1, round(width * scale)),
                    max(1, round(height * scale)),
                )
                prepared = prepared.resize(resized, Image.Resampling.LANCZOS)

        prepared.save(output_path, format="PNG")

    return output_path
