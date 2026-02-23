#!/usr/bin/env bash
set -euo pipefail

APP_NAME="mortal_mac_v0.2"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_PATH="$ROOT/dist/${APP_NAME}.app"
DMG_PATH="$ROOT/dist/${APP_NAME}.dmg"
STAGE_DIR="$ROOT/dist/.dmg-stage-${APP_NAME}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must run on macOS." >&2
  exit 1
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "App bundle not found: $APP_PATH" >&2
  echo "Run scripts/generate_mac_app.sh first."
  exit 1
fi

rm -rf "$STAGE_DIR" "$DMG_PATH"
mkdir -p "$STAGE_DIR"

cp -R "$APP_PATH" "$STAGE_DIR/"
ln -s /Applications "$STAGE_DIR/Applications"

hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGE_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

rm -rf "$STAGE_DIR"
echo "Built DMG: $DMG_PATH"
