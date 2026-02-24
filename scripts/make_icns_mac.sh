#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_PNG="$ROOT/resources/icon.png"
OUT_ICNS="$ROOT/resources/icon.icns"
ICONSET_DIR="$ROOT/build/icon.iconset"

if [[ ! -f "$SRC_PNG" ]]; then
  echo "Missing source icon: $SRC_PNG" >&2
  exit 1
fi

if ! command -v sips >/dev/null 2>&1 || ! command -v iconutil >/dev/null 2>&1; then
  echo "sips/iconutil not found. Skipping icon.icns generation."
  exit 0
fi

rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

sips -z 16 16 "$SRC_PNG" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32 "$SRC_PNG" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$SRC_PNG" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64 "$SRC_PNG" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$SRC_PNG" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256 "$SRC_PNG" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$SRC_PNG" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512 "$SRC_PNG" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$SRC_PNG" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$SRC_PNG" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null

iconutil -c icns "$ICONSET_DIR" -o "$OUT_ICNS"
echo "Generated icon: $OUT_ICNS"
