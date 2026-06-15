# Smart OCR Quality Report

Measured on the versioned fixture corpus in
`workers/tests/fixtures/ocr/manifest.json`. The frozen pre-smart baseline comes
from `workers/tests/fixtures/ocr/pre-smart-baseline.json`.

Local measurements were captured on macOS 14.6.1 arm64 with Python 3.12 and
ONNX Runtime CPU inference.

## Quality

| Metric | Pre-smart baseline | Smart OCR |
| --- | ---: | ---: |
| Exact-line accuracy | 0.625 | 0.750 |
| Character error rate | 0.275213 | 0.053385 |
| Latin retry rate | Not measured | 43.75% (14 of 32 detected lines) |
| PP-OCRv6 retry rate | Not measured | 43.75% (14 of 32 detected lines) |
| Average time per fixture | Not measured | 44.86 seconds |

Release requirements:

- overall exact-line accuracy must not regress;
- overall character error rate must not regress;
- `ru-en-mixed.png` must improve by at least one metric;
- strong lines must not invoke fallback recognizers;
- manual Cyrillic and Latin modes must invoke only their selected recognizer.

The final local benchmark passed on June 15, 2026. Mixed Russian/English
recognition improved from 0.0 to 1.0 exact-line accuracy and from 0.727273 to
0.0 character error rate.

## Artifact Sizes

| Artifact | Measured size |
| --- | ---: |
| `MDify-Lite-AppleSilicon.zip` | 72,469,349 bytes |
| `MDify-OCR-AppleSilicon.zip` | 305,340,107 bytes |
| `MDify-Lite-Intel.zip` | 75,896,108 bytes |
| `MDify-OCR-Intel.zip` | 298,120,344 bytes |
| `MDify-Windows-Lite-Setup.exe` | 136,713,318 bytes |
| `MDify-Windows-OCR-Setup.exe` | 319,454,444 bytes |

## Verification Status

Automated locally:

- PP-OCRv6 and all manifest models pass SHA-256 verification.
- Smart OCR quality is gated against a frozen pre-smart baseline.
- macOS Lite contains only the Lite worker and no PaddleOCR models.
- macOS OCR contains only the OCR worker, its manifest, and every manifest model.
- GitHub Actions passed on June 15, 2026 for macOS Apple Silicon, macOS Intel,
  Windows Lite, and Windows OCR.
- Windows CI built, tested, published, inspected, and packaged Lite and OCR
  separately into two Inno Setup installers.

The following hardware acceptance checks are intentionally deferred from the
v0.4.0 automated release gate:

- run Windows OCR on a clean Windows 10 version 1809 or newer x64 VM;
- install Windows Lite on a clean supported Copilot+ PC;
- run `--diagnose-native-ocr` and confirm whether native OCR works without package identity;
- add and validate a signed sparse identity companion only if that clean-machine
  test proves it is required.
