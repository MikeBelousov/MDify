from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any


@dataclass(frozen=True)
class OCRWord:
    text: str
    left: float
    right: float
    top: float
    bottom: float

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2.0

    @property
    def height(self) -> float:
        return max(1.0, self.bottom - self.top)


def markdown_from_rapidocr_output(output: Any) -> str:
    boxes = getattr(output, "boxes", None)
    txts = getattr(output, "txts", None)
    if boxes is None or txts is None:
        return ""

    try:
        box_list = list(boxes)
        text_list = list(txts)
    except TypeError:
        return ""

    if not box_list or len(box_list) != len(text_list):
        return ""

    words: list[OCRWord] = []
    for box, raw_text in zip(box_list, text_list):
        text = str(raw_text).strip()
        if not text:
            continue

        try:
            points = [(float(point[0]), float(point[1])) for point in box]
        except (TypeError, ValueError, IndexError):
            return ""
        if len(points) < 4:
            return ""

        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        words.append(
            OCRWord(
                text=text,
                left=min(xs),
                right=max(xs),
                top=min(ys),
                bottom=max(ys),
            )
        )

    if not words:
        return ""

    words.sort(key=lambda word: (word.center_y, word.left))
    median_height = median(word.height for word in words)
    line_tolerance = max(8.0, median_height * 0.7)

    lines: list[list[OCRWord]] = []
    current: list[OCRWord] = []
    current_center = 0.0
    for word in words:
        if not current:
            current = [word]
            current_center = word.center_y
            continue

        if abs(word.center_y - current_center) <= line_tolerance:
            current.append(word)
            current_center = sum(item.center_y for item in current) / len(current)
        else:
            lines.append(current)
            current = [word]
            current_center = word.center_y

    if current:
        lines.append(current)

    parts: list[str] = []
    previous_bottom: float | None = None
    blank_gap = max(18.0, median_height * 1.8)
    for line in lines:
        sorted_line = sorted(line, key=lambda word: word.left)
        line_top = min(word.top for word in sorted_line)
        line_bottom = max(word.bottom for word in sorted_line)
        if previous_bottom is not None and line_top - previous_bottom > blank_gap:
            parts.append("")
        parts.append(" ".join(word.text for word in sorted_line))
        previous_bottom = line_bottom

    return "\n".join(parts).strip()
