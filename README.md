# MDify

MDify is a native desktop app for converting local documents to Markdown.

The macOS app is built with SwiftUI. The Windows preview app is built with WPF.
Both use bundled Python workers for document conversion.

## Install

Download release assets from the latest GitHub release:

https://github.com/MikeBelousov/MDify/releases/latest

### macOS

- `MDify-Lite-AppleSilicon.zip`: smaller build for Apple Silicon Macs.
- `MDify-Lite-Intel.zip`: smaller build for Intel Macs.
- `MDify-OCR-AppleSilicon.zip`: larger build with local RapidOCR models for Apple Silicon Macs.
- `MDify-OCR-Intel.zip`: larger build with local RapidOCR models for Intel Macs.

Unzip it, move the app to `/Applications`, and open it.

The release is unsigned and not notarized. If macOS blocks first launch, run one
of these commands:

```bash
xattr -dr com.apple.quarantine "/Applications/MDify Lite.app"
open -a "MDify Lite"
```

```bash
xattr -dr com.apple.quarantine "/Applications/MDify OCR.app"
open -a "MDify OCR"
```

### Windows Preview

The Windows build is distributed as an unsigned preview for Windows 11 x64:

- `MDifySetup.exe`: installs MDify to `%LOCALAPPDATA%\Programs\MDify`.

Windows SmartScreen may warn because the preview executable is unsigned. Native
Windows AI OCR is attempted first for images and scanned PDFs, and may need
model preparation the first time it runs. If Windows AI OCR is unavailable,
blocked by capability/model readiness, or returns weak text, MDify falls back to
the bundled RapidOCR worker.

Native OCR can be checked from the command line:

```powershell
MDify.Windows.exe --diagnose-native-ocr "C:\path\sample.png"
```

## Requirements

- macOS 14+
- Windows 11 x64 for the Windows preview build.

## Variants

`MDify Lite.app` supports document conversion and native Apple Vision OCR:

- `pdf`, `docx`, `pptx`, `xlsx`, `xls`
- `html`, `htm`, `csv`, `json`, `xml`, `txt`, `md`
- `epub`, `zip`
- `jpg`, `jpeg`, `png`, `tif`, `tiff`, `webp`, `bmp`

`MDify OCR.app` supports the same formats and adds RapidOCR fallback via
ONNX Runtime and pypdfium2 when Apple Vision output is weak.

`MDify.Windows.exe` uses the OCR policy by default. It supports the same input
formats, uses Windows AI Text Recognizer when available, and falls back to the
bundled RapidOCR worker when native OCR is unavailable or weak.

## Features

- Add individual local files.
- Add a whole folder from the toolbar, menu, or drag-and-drop.
- Skip unsupported, hidden, system, package, and symlink entries during folder import.
- Confirm whether folder import should include subfolders.
- Preserve folder structure when writing Markdown outputs.
- Preview, copy, and reveal generated Markdown.

Folder imports are written under the selected output folder. By default that is
Downloads. For example, importing `Research/Notes/source.txt` writes to
`~/Downloads/Research/Notes/source.md`.


## Homebrew Install

The intended first release install commands are:

```bash
brew install --cask mikebelousov/tap/mdify
brew install --cask mikebelousov/tap/mdify-ocr
```


## License

MIT. See `LICENSE` and `ThirdPartyNotices.md`.
