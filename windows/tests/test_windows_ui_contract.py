from __future__ import annotations

from pathlib import Path


MAIN_WINDOW = Path("windows/MDify.Windows/MainWindow.xaml")


def test_read_only_text_boxes_use_one_way_binding() -> None:
    xaml = MAIN_WINDOW.read_text(encoding="utf-8")

    assert 'Text="{Binding PreviewText, Mode=OneWay}"' in xaml
    assert 'Text="{Binding LogText, Mode=OneWay}"' in xaml
