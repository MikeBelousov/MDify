# Changelog

## Unreleased

- Automatic OCR now starts with Eslavic PP-OCRv5 and accepts Latin rescues only
  when strict confidence, quality, and text-similarity guards all pass.
- Removed PP-OCRv6 model files from OCR release bundles and added exact manifest
  checks for macOS and Windows artifacts.
- Fixed the retained PP-OCRv6 adapter's PIL RGB and NumPy BGR input contract.

## v0.4.2 - 2026-06-22

- Made the macOS conversion action clearer with a prominent dark Convert button.
- Added a Convert call-to-action to the pending Markdown preview state.

## v0.4.1 - 2026-06-20

- Windows OCR no longer crashes when opening the Log tab.
- Windows Lite now installs on Windows 11 and reports Windows AI OCR availability inside the app.

## v0.4.0 - 2026-06-15

- MDify now comes in separate Lite and OCR versions for both macOS and Windows.
- OCR versions recognize mixed Cyrillic and Latin text more accurately and let you choose the language manually.
- Windows OCR now works on Windows 10 version 1809 and newer.
- Windows Lite and Windows OCR have separate installers and can be installed side by side.

## v0.3.0 - 2026-06-05

- Added the first Windows version of MDify.
- Added Windows AI OCR for images and scanned PDFs.
- Added a simple Windows installer.

## v0.2.0 - 2026-06-02

- Added separate Lite and OCR versions for macOS.
- Added local OCR for images and scanned PDFs.
- MDify no longer needs Python to be installed separately.

## v0.1.0 - 2026-06-02

- First public release for macOS.
- Convert individual files or whole folders to Markdown.
- Preview, copy, and reveal converted files in Finder.
