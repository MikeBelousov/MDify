from __future__ import annotations

from pathlib import Path

from markitdown import MarkItDown

from workers.common.markdown_postprocess import normalize_markdown


def convert_with_markitdown(input_path: Path) -> str:
    result = MarkItDown().convert(str(input_path))
    text = getattr(result, "text_content", None)
    if text is None:
        text = str(result)
    return normalize_markdown(text)


def write_markdown(output_path: Path, markdown: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
