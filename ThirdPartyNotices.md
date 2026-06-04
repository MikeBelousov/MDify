# Third Party Notices

MDify bundles Python workers built with PyInstaller. Runtime does not create a
virtual environment, install packages, or download models on the user's machine.

## Lite Worker

- Microsoft MarkItDown 0.1.6: MIT.
- pdfminer.six 20251230: MIT.
- PyInstaller 6.20.0: GPLv2-or-later with PyInstaller's bootloader exception.

## OCR Worker

The OCR worker includes all Lite worker dependencies plus:

- RapidOCR 3.8.1: Apache-2.0.
- ONNX Runtime 1.22.1: MIT.
- pypdfium2 5.9.0: BSD-3-Clause, Apache-2.0, and dependency licenses.
- Pillow 12.2.0: HPND-style Pillow license.
- NumPy 2.4.6: BSD-3-Clause.
- opencv-python 4.13.0.92 and opencv-python-headless 4.13.0.92: Apache-2.0.

OCR model files are listed in `workers/ocr/model_manifest.json` with source URLs,
sha256 hashes, and license notes. The OCR release embeds those files in
`MDify OCR.app`; runtime never downloads them.

Before publishing binary releases, regenerate a complete dependency notice from
the locked worker environments.
