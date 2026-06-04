#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PRODUCT="MDify"
MIN_SYSTEM_VERSION="14.0"
APP_VERSION="${APP_VERSION:-0.2.0}"
BUILD_NUMBER="${BUILD_NUMBER:-2}"
DIST_DIR="$ROOT_DIR/dist"

VARIANT="all"
ARCH="all"
SWIFT_BINARY=""

usage() {
  echo "usage: $0 [--variant lite|ocr|all] [--arch arm64|x86_64|all]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --variant)
      VARIANT="${2:-}"
      shift 2
      ;;
    --arch)
      ARCH="${2:-}"
      shift 2
      ;;
    lite|ocr|all)
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
  lite|ocr|all) ;;
  *)
    usage
    exit 2
    ;;
esac

case "$ARCH" in
  arm64|x86_64|all) ;;
  *)
    usage
    exit 2
    ;;
esac

if [[ -z "${DEVELOPER_DIR:-}" && -d "$HOME/Desktop/Xcode.app/Contents/Developer" ]]; then
  export DEVELOPER_DIR="$HOME/Desktop/Xcode.app/Contents/Developer"
fi

variants_for_release() {
  case "$VARIANT" in
    lite) echo "lite" ;;
    ocr) echo "ocr" ;;
    all) echo "lite ocr" ;;
  esac
}

app_name_for_variant() {
  case "$1" in
    lite) echo "MDify Lite" ;;
    ocr) echo "MDify OCR" ;;
  esac
}

bundle_id_for_variant() {
  case "$1" in
    lite) echo "com.mihailbelousov.MDifyLite" ;;
    ocr) echo "com.mihailbelousov.MDifyOCR" ;;
  esac
}

archs_for_release() {
  case "$1" in
    arm64) echo "arm64" ;;
    x86_64) echo "x86_64" ;;
    all) echo "arm64 x86_64" ;;
  esac
}

arch_label() {
  case "$1" in
    arm64) echo "AppleSilicon" ;;
    x86_64) echo "Intel" ;;
  esac
}

zip_name_for_variant() {
  local worker_kind="$1"
  local target_arch="$2"
  local label
  label="$(arch_label "$target_arch")"
  case "$worker_kind" in
    lite) echo "MDify-Lite-$label.zip" ;;
    ocr) echo "MDify-OCR-$label.zip" ;;
  esac
}

write_info_plist() {
  local plist="$1"
  local app_name="$2"
  local bundle_id="$3"
  local worker_kind="$4"

  cat >"$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>$APP_PRODUCT</string>
  <key>CFBundleIdentifier</key>
  <string>$bundle_id</string>
  <key>CFBundleName</key>
  <string>$app_name</string>
  <key>CFBundleDisplayName</key>
  <string>$app_name</string>
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
  <string>$worker_kind</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
</dict>
</plist>
PLIST
}

build_swift_binary() {
  local target_arch="$1"
  swift build -c release --product "$APP_PRODUCT" --arch "$target_arch"
  local bin_path
  bin_path="$(swift build -c release --product "$APP_PRODUCT" --arch "$target_arch" --show-bin-path)"
  SWIFT_BINARY="$bin_path/$APP_PRODUCT"
}

verify_single_arch() {
  local path="$1"
  local expected_arch="$2"
  local label="$3"
  local actual_archs

  actual_archs="$(lipo -archs "$path" 2>/dev/null || true)"
  if [[ "$actual_archs" != "$expected_arch" ]]; then
    echo "$label architecture mismatch: $path" >&2
    echo "Expected: $expected_arch" >&2
    echo "Actual: ${actual_archs:-unknown}" >&2
    file "$path" >&2 || true
    exit 1
  fi
}

build_variant() {
  local worker_kind="$1"
  local target_arch="$2"
  local swift_binary="$3"
  local app_name
  local bundle_id
  local zip_name
  app_name="$(app_name_for_variant "$worker_kind")"
  bundle_id="$(bundle_id_for_variant "$worker_kind")"
  zip_name="$(zip_name_for_variant "$worker_kind" "$target_arch")"

  local app_bundle="$DIST_DIR/$app_name.app"
  local app_contents="$app_bundle/Contents"
  local app_macos="$app_contents/MacOS"
  local app_resources="$app_contents/Resources"
  local app_binary="$app_macos/$APP_PRODUCT"
  local worker_name="mdify-worker-$worker_kind"
  local worker_bundle="$ROOT_DIR/.build/workers/$target_arch/$worker_name"

  "$ROOT_DIR/workers/build/build_worker.sh" --variant "$worker_kind" --target-arch "$target_arch"

  rm -rf "$app_bundle" "$DIST_DIR/$zip_name"
  mkdir -p "$app_macos" "$app_resources/Workers"
  cp "$swift_binary" "$app_binary"
  chmod +x "$app_binary"
  cp -R "$worker_bundle" "$app_resources/Workers/$worker_name"

  if [[ -f "$ROOT_DIR/Resources/MDifyIcon.icns" ]]; then
    cp "$ROOT_DIR/Resources/MDifyIcon.icns" "$app_resources/MDifyIcon.icns"
  fi

  write_info_plist "$app_contents/Info.plist" "$app_name" "$bundle_id" "$worker_kind"
  verify_single_arch "$app_binary" "$target_arch" "App binary"
  verify_single_arch "$app_resources/Workers/$worker_name/$worker_name" "$target_arch" "Worker"
  ditto -c -k --keepParent "$app_bundle" "$DIST_DIR/$zip_name"

  echo "Built $app_bundle"
  echo "Built $DIST_DIR/$zip_name"
  lipo -archs "$app_binary"
  file "$app_resources/Workers/$worker_name/$worker_name"
}

mkdir -p "$DIST_DIR"

for target_arch in $(archs_for_release "$ARCH"); do
  build_swift_binary "$target_arch"
  for variant in $(variants_for_release); do
    build_variant "$variant" "$target_arch" "$SWIFT_BINARY"
  done
done
