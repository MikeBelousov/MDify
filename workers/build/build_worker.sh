#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VARIANT="lite"
PYTHON_BIN="${PYTHON_BIN:-/usr/local/bin/python3}"
HOST_ARCH="$(uname -m)"
TARGET_ARCH="${TARGET_ARCH:-$HOST_ARCH}"

usage() {
  echo "usage: $0 [--variant lite|ocr] [--target-arch arm64|x86_64]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --variant)
      VARIANT="${2:-}"
      shift 2
      ;;
    --target-arch)
      TARGET_ARCH="${2:-}"
      shift 2
      ;;
    lite|ocr)
      VARIANT="$1"
      shift
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

case "$VARIANT" in
  lite|ocr) ;;
  *)
    usage
    exit 2
    ;;
esac

case "$TARGET_ARCH" in
  arm64|x86_64) ;;
  *)
    usage
    exit 2
    ;;
esac

PYTHON_MACHINE="$("$PYTHON_BIN" -c 'import platform; print(platform.machine())')"
PYTHON_EXECUTABLE="$("$PYTHON_BIN" -c 'import sys; print(sys.executable)')"

if [[ "$PYTHON_MACHINE" != "$TARGET_ARCH" ]]; then
  cat >&2 <<EOF
Cannot build $VARIANT worker for $TARGET_ARCH with Python running as $PYTHON_MACHINE.
PYTHON_BIN: $PYTHON_BIN
Python executable: $PYTHON_EXECUTABLE
Run with a $TARGET_ARCH Python interpreter, or invoke a universal Python under that architecture.
EOF
  exit 1
fi

VENV_DIR="$ROOT_DIR/.build/worker-${VARIANT}-${TARGET_ARCH}-venv"
WORK_DIR="$ROOT_DIR/.build/pyinstaller-${VARIANT}-${TARGET_ARCH}"
DIST_DIR="$ROOT_DIR/.build/workers/$TARGET_ARCH"
ENTRY="$ROOT_DIR/workers/$VARIANT/mdify_worker_${VARIANT}.py"
REQUIREMENTS="$ROOT_DIR/workers/$VARIANT/requirements-${VARIANT}.txt"
NAME="mdify-worker-$VARIANT"

"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$REQUIREMENTS"

if [[ "$VARIANT" == "ocr" ]]; then
  "$VENV_DIR/bin/python" "$ROOT_DIR/workers/build/download_models.py"
fi

PYINSTALLER_ARGS=(
  --clean
  --noconfirm
  --onedir
  --name "$NAME"
  --distpath "$DIST_DIR"
  --workpath "$WORK_DIR"
  --specpath "$WORK_DIR"
  --paths "$ROOT_DIR"
  --target-arch "$TARGET_ARCH"
  --collect-all markitdown
  --collect-all magika
  "$ENTRY"
)

if [[ "$VARIANT" == "ocr" ]]; then
  PYINSTALLER_ARGS+=(
    --collect-all rapidocr
    --collect-all onnxruntime
    --collect-all cv2
    --collect-all pypdfium2
    --collect-all PIL
    --add-data "$ROOT_DIR/workers/ocr/model_manifest.json:workers/ocr"
    --add-data "$ROOT_DIR/workers/ocr/models:workers/ocr/models"
  )
fi

if ! "$VENV_DIR/bin/python" -m PyInstaller "${PYINSTALLER_ARGS[@]}"; then
  cat >&2 <<EOF
PyInstaller failed while building $VARIANT worker for $TARGET_ARCH.
PYTHON_BIN: $PYTHON_BIN
Python executable: $PYTHON_EXECUTABLE
TARGET_ARCH: $TARGET_ARCH
Check that the Python interpreter and installed wheels support $TARGET_ARCH.
EOF
  exit 1
fi

BUILT_WORKER="$DIST_DIR/$NAME/$NAME"
if [[ ! -x "$BUILT_WORKER" ]]; then
  echo "PyInstaller did not create executable worker: $BUILT_WORKER" >&2
  exit 1
fi

ACTUAL_ARCHS="$(lipo -archs "$BUILT_WORKER" 2>/dev/null || true)"
if [[ "$ACTUAL_ARCHS" != "$TARGET_ARCH" ]]; then
  echo "Worker architecture mismatch for $BUILT_WORKER" >&2
  echo "Expected: $TARGET_ARCH" >&2
  echo "Actual: ${ACTUAL_ARCHS:-unknown}" >&2
  file "$BUILT_WORKER" >&2 || true
  exit 1
fi

echo "$BUILT_WORKER"
