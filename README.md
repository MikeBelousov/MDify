# MDify

MDify turns documents into Markdown on macOS and Windows. Everything runs
locally, so your files are never uploaded anywhere.

## Download

Get the latest version from:

https://github.com/MikeBelousov/MDify/releases/latest

Not sure which one to choose?

| Version | Best for |
| --- | --- |
| macOS Lite | Most Mac users. It uses Apple's built-in OCR. |
| macOS OCR | Scans and images that need stronger OCR or manual language selection. |
| Windows OCR | Most Windows users. It works on Windows 10 and 11. |
| Windows Lite | Supported Copilot+ PCs that can use Windows AI OCR. |

The OCR versions are larger because they include all recognition models and
work without an internet connection.

### macOS

- Apple Silicon: `MDify-Lite-AppleSilicon.zip` or `MDify-OCR-AppleSilicon.zip`
- Intel: `MDify-Lite-Intel.zip` or `MDify-OCR-Intel.zip`

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

### Windows

- `MDify-Windows-OCR-Setup.exe`: recommended for most Windows 10 and 11 PCs.
- `MDify-Windows-Lite-Setup.exe`: for Windows 11 PCs that may support Windows AI OCR.

Both are regular `.exe` installers and can be installed side by side. Windows
SmartScreen may show a warning because the installers are not signed yet.

Windows Lite installs on Windows 11, but its built-in OCR only works on a
supported Copilot+ PC with a compatible NPU and a supported Windows 11 25H2
build. If Windows AI OCR is not available, the app will tell you to use Windows
OCR instead. Windows OCR works on Windows 10 version 1809 and newer.

To check whether Windows AI OCR is available:

```powershell
MDify.Windows.exe --diagnose-native-ocr "C:\path\sample.png"
```

## Features

- Add individual local files.
- Add a whole folder from the toolbar, menu, or drag-and-drop.
- Convert documents, spreadsheets, presentations, web pages, ebooks, and images.
- Recognize text in images and scanned PDFs.
- Choose Automatic, Cyrillic, or Latin recognition in OCR versions.
- Preserve folder structure when writing Markdown outputs.
- Preview, copy, and reveal generated Markdown.

Folder imports are written under the selected output folder. By default that is
Downloads. For example, importing `Research/Notes/source.txt` writes to
`~/Downloads/Research/Notes/source.md`.

Supported formats include `pdf`, `docx`, `pptx`, `xlsx`, `xls`, `html`, `csv`,
`json`, `xml`, `txt`, `md`, `epub`, `zip`, `jpg`, `png`, `tiff`, `webp`, and
`bmp`.

## Requirements

- macOS 14 or newer
- Windows OCR: Windows 10 version 1809 or newer, x64
- Windows Lite: Windows 11 for installation; supported Copilot+ PC with a compatible NPU for OCR

For OCR quality measurements and release verification details, see
[`docs/ocr-quality-report.md`](docs/ocr-quality-report.md).

## License

MIT. See `LICENSE` and `ThirdPartyNotices.md`.
