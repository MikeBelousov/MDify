# Changelog

## v0.2.0 - 2026-06-02

- Replaced user-machine Python setup with embedded PyInstaller workers.
- Added separate `MDify Lite.app` and `MDify OCR.app` release variants.
- Added local OCR for image files and scanned PDFs with bundled RapidOCR models.
- Updated folder import support so Lite and OCR variants expose different supported extensions.
- Added worker JSON protocol, Swift worker client, and release packaging for separate zip assets.

## v0.1.0 - 2026-06-02

- Initial public release of MDify.
- Native macOS SwiftUI app for converting local documents to Markdown.
- Automatic MarkItDown setup inside an app-owned Python virtual environment.
- File and folder import with unsupported-file filtering.
- Mirrored output folders for folder imports.
- Markdown preview, raw output, copy, and Finder reveal actions.
