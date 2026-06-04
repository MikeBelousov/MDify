# MDify

MDify is a native macOS app for converting local documents to Markdown. It ships
with an embedded Python worker, so users do not install Python or run `pip`.

MDify is not a Microsoft product. The Lite worker uses Microsoft's MarkItDown
library for supported document formats.

## Install

Download the release asset for your Mac from the latest GitHub release:

- [`MDify-Lite-AppleSilicon.zip`](dist/MDify-Lite-AppleSilicon.zip): smaller build for Apple Silicon Macs.
- [`MDify-Lite-Intel.zip`](dist/MDify-Lite-Intel.zip): smaller build for Intel Macs.
- [`MDify-OCR-AppleSilicon.zip`](dist/MDify-OCR-AppleSilicon.zip): larger build with local RapidOCR models for Apple Silicon Macs.
- [`MDify-OCR-Intel.zip`](dist/MDify-OCR-Intel.zip): larger build with local RapidOCR models for Intel Macs.

https://github.com/MikeBelousov/MDify/releases

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

## Requirements

- macOS 14+
- No user-installed Python required
- For development: Xcode 16.2 recommended, Python 3.12 for worker builds

## Variants

`MDify Lite.app` supports document conversion and native Apple Vision OCR:

- `pdf`, `docx`, `pptx`, `xlsx`, `xls`
- `html`, `htm`, `csv`, `json`, `xml`, `txt`, `md`
- `epub`, `zip`
- `jpg`, `jpeg`, `png`, `tif`, `tiff`, `webp`, `bmp`

`MDify OCR.app` supports the same formats and adds RapidOCR fallback via
ONNX Runtime and pypdfium2 when Apple Vision output is weak.

The OCR build embeds model files under the app bundle. Runtime never downloads
models.

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

## Build and Run

```bash
./script/build_and_run.sh
```

The script builds the SwiftPM app, stages `dist/MDify Lite.app` by default, and
launches it as a normal macOS application bundle for development. Pass
`--variant ocr` to run `dist/MDify OCR.app`.

You can also open the project in Xcode by opening `Package.swift`. A separate
`.xcodeproj` is not required for development; SwiftPM is the project entrypoint.

If Xcode lives on the Desktop, the scripts use:

```bash
DEVELOPER_DIR=~/Desktop/Xcode.app/Contents/Developer
```

## Build Workers

```bash
./workers/build/build_worker.sh --variant lite --target-arch arm64
./workers/build/build_worker.sh --variant ocr --target-arch arm64
```

Worker builds target the current host architecture by default. You can override
that with `--target-arch arm64`, `--target-arch x86_64`, or the `TARGET_ARCH`
environment variable. The selected Python interpreter must run as the target
architecture so PyInstaller collects matching binary wheels.

The OCR build expects model files in `workers/ocr/models`. To download or verify
them from the manifest:

```bash
python3 workers/build/download_models.py
python3 workers/build/download_models.py --verify-only
```

OCR model files should be tracked with Git LFS before publishing.

## Build Release Archives

```bash
./script/build_release.sh --variant all --arch all
```

Release archives are written to:

- `dist/MDify-Lite-AppleSilicon.zip`
- `dist/MDify-Lite-Intel.zip`
- `dist/MDify-OCR-AppleSilicon.zip`
- `dist/MDify-OCR-Intel.zip`

## Future Homebrew Install

The intended first release install commands are:

```bash
brew install --cask mikebelousov/tap/mdify
brew install --cask mikebelousov/tap/mdify-ocr
```

Cask templates are in `homebrew/mdify.rb` and `homebrew/mdify-ocr.rb`. Update
the Apple Silicon and Intel sha256 values after publishing the GitHub release
assets.

## License

MIT. See `LICENSE` and `ThirdPartyNotices.md`.
