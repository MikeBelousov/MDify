from __future__ import annotations

from pathlib import Path


CONTENT_VIEW = Path("Sources/MDify/Views/ContentView.swift")
CONVERT_BUTTON = Path("Sources/MDify/Views/ConvertButton.swift")
MARKDOWN_PREVIEW = Path("Sources/MDify/Views/MarkdownPreviewView.swift")


def test_convert_button_matches_primary_markdown_action_contract() -> None:
    assert CONVERT_BUTTON.exists(), "ConvertButton.swift should define the shared Convert CTA"

    source = CONVERT_BUTTON.read_text(encoding="utf-8")

    assert 'Label("Convert", systemImage: "number")' in source
    assert ".labelStyle(.titleAndIcon)" in source
    assert ".buttonStyle(.borderedProminent)" in source
    assert ".tint(Self.brandBackground)" in source
    assert 'Color(red: 17 / 255, green: 24 / 255, blue: 39 / 255)' in source
    assert '.help("Convert to Markdown")' in source
    assert '.accessibilityLabel("Convert to Markdown")' in source


def test_toolbar_uses_convert_button_without_changing_neighbor_actions() -> None:
    source = CONTENT_VIEW.read_text(encoding="utf-8")

    assert "ConvertButton {" in source
    assert 'Label("Convert All", systemImage: "arrow.triangle.2.circlepath")' not in source
    assert 'Label("Add Files", systemImage: "plus")' in source
    assert 'Label("Add Folder", systemImage: "folder.badge.plus")' in source
    assert 'Label("Output", systemImage: "folder")' in source
    assert 'Label("Cancel", systemImage: "stop")' in source
    assert 'Label("Copy Markdown", systemImage: "doc.on.doc")' in source
    assert 'Label("Show in Finder", systemImage: "finder")' in source


def test_pending_markdown_preview_exposes_contextual_convert_cta() -> None:
    source = MARKDOWN_PREVIEW.read_text(encoding="utf-8")

    assert "PendingConversionView" in source
    assert "case .pending where item.markdownText.isEmpty:" in source
    assert "ConvertButton {" in source
    assert "Task { await appState.convertAll() }" in source
