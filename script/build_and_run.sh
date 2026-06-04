#!/usr/bin/env bash
set -euo pipefail

MODE="run"
VARIANT="lite"
APP_PRODUCT="MDify"
MIN_SYSTEM_VERSION="14.0"
APP_VERSION="${APP_VERSION:-0.2.0}"
BUILD_NUMBER="${BUILD_NUMBER:-2}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
TARGET_ARCH="$(uname -m)"
WORKER_NAME="mdify-worker-$VARIANT"
WORKER_BUILD_DIR="$ROOT_DIR/.build/workers/$TARGET_ARCH/$WORKER_NAME"
APP_NAME="MDify Lite"
BUNDLE_ID="com.mihailbelousov.MDifyLite"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
APP_CONTENTS="$APP_BUNDLE/Contents"
APP_MACOS="$APP_CONTENTS/MacOS"
APP_RESOURCES="$APP_CONTENTS/Resources"
APP_BINARY="$APP_MACOS/$APP_PRODUCT"
INFO_PLIST="$APP_CONTENTS/Info.plist"

usage() {
  echo "usage: $0 [run|--debug|--logs|--telemetry|--verify] [--variant lite|ocr]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    run|--debug|debug|--logs|logs|--telemetry|telemetry|--verify|verify)
      MODE="$1"
      shift
      ;;
    --variant)
      VARIANT="${2:-}"
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
  lite)
    APP_NAME="MDify Lite"
    BUNDLE_ID="com.mihailbelousov.MDifyLite"
    ;;
  ocr)
    APP_NAME="MDify OCR"
    BUNDLE_ID="com.mihailbelousov.MDifyOCR"
    ;;
  *)
    usage
    exit 2
    ;;
esac

WORKER_NAME="mdify-worker-$VARIANT"
WORKER_BUILD_DIR="$ROOT_DIR/.build/workers/$TARGET_ARCH/$WORKER_NAME"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
APP_CONTENTS="$APP_BUNDLE/Contents"
APP_MACOS="$APP_CONTENTS/MacOS"
APP_RESOURCES="$APP_CONTENTS/Resources"
APP_BINARY="$APP_MACOS/$APP_PRODUCT"
INFO_PLIST="$APP_CONTENTS/Info.plist"

if [[ -z "${DEVELOPER_DIR:-}" && -d "$HOME/Desktop/Xcode.app/Contents/Developer" ]]; then
  export DEVELOPER_DIR="$HOME/Desktop/Xcode.app/Contents/Developer"
fi

pkill -x "$APP_PRODUCT" >/dev/null 2>&1 || true

swift build --product "$APP_PRODUCT" --arch "$TARGET_ARCH"
BUILD_BINARY="$(swift build --product "$APP_PRODUCT" --arch "$TARGET_ARCH" --show-bin-path)/$APP_PRODUCT"

if [[ ! -x "$WORKER_BUILD_DIR/$WORKER_NAME" ]]; then
  "$ROOT_DIR/workers/build/build_worker.sh" --variant "$VARIANT" --target-arch "$TARGET_ARCH"
fi

rm -rf "$APP_BUNDLE"
mkdir -p "$APP_MACOS" "$APP_RESOURCES/Workers"
cp "$BUILD_BINARY" "$APP_BINARY"
chmod +x "$APP_BINARY"
cp -R "$WORKER_BUILD_DIR" "$APP_RESOURCES/Workers/$WORKER_NAME"

if [[ -f "$ROOT_DIR/Resources/MDifyIcon.icns" ]]; then
  cp "$ROOT_DIR/Resources/MDifyIcon.icns" "$APP_RESOURCES/MDifyIcon.icns"
fi

cat >"$INFO_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>$APP_PRODUCT</string>
  <key>CFBundleIdentifier</key>
  <string>$BUNDLE_ID</string>
  <key>CFBundleName</key>
  <string>$APP_NAME</string>
  <key>CFBundleDisplayName</key>
  <string>$APP_NAME</string>
  <key>CFBundleIconFile</key>
  <string>MDifyIcon</string>
  <key>CFBundleShortVersionString</key>
  <string>$APP_VERSION</string>
  <key>CFBundleVersion</key>
  <string>$BUILD_NUMBER</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>$MIN_SYSTEM_VERSION</string>
  <key>MDifyWorkerKind</key>
  <string>$VARIANT</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
</dict>
</plist>
PLIST

open_app() {
  /usr/bin/open -n "$APP_BUNDLE"
}

case "$MODE" in
  run)
    open_app
    ;;
  --debug|debug)
    lldb -- "$APP_BINARY"
    ;;
  --logs|logs)
    open_app
    /usr/bin/log stream --info --style compact --predicate "process == \"$APP_PRODUCT\""
    ;;
  --telemetry|telemetry)
    open_app
    /usr/bin/log stream --info --style compact --predicate "subsystem == \"$BUNDLE_ID\""
    ;;
  --verify|verify)
    open_app
    sleep 1
    pgrep -x "$APP_PRODUCT" >/dev/null
    ;;
  *)
    usage
    exit 2
    ;;
esac
