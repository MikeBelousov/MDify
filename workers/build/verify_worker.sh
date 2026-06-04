#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VARIANT="${1:-lite}"
WORKER="$ROOT_DIR/.build/workers/mdify-worker-$VARIANT/mdify-worker-$VARIANT"

if [[ ! -x "$WORKER" ]]; then
  echo "worker not found: $WORKER" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
INPUT="$TMP_DIR/input.txt"
OUTPUT="$TMP_DIR/output.md"
echo "Hello MDify" > "$INPUT"
"$WORKER" --input "$INPUT" --output "$OUTPUT" --format json
test -s "$OUTPUT"
