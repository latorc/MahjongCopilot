#!/usr/bin/env bash
set -euo pipefail

APP_NAME="mortal_mac_v0.2"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT/.venv-mac"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
REQUIRED_PY_MINOR="3.11"
BROWSERS_CACHE_DIR="$ROOT/.playwright-browsers"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script must run on macOS." >&2
  exit 1
fi

cd "$ROOT"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Missing required interpreter: $PYTHON_BIN" >&2
  echo "Install Python $REQUIRED_PY_MINOR first, then rerun."
  exit 1
fi

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import tkinter
PY
then
  if command -v brew >/dev/null 2>&1; then
    echo "Python is missing tkinter, installing python-tk@${REQUIRED_PY_MINOR}..."
    brew install "python-tk@${REQUIRED_PY_MINOR}"
  else
    echo "Python is missing tkinter and Homebrew is unavailable." >&2
    echo "Install a tkinter-enabled Python ${REQUIRED_PY_MINOR} first, then rerun."
    exit 1
  fi
fi

RECREATE_VENV=0
if [[ -x "$VENV_DIR/bin/python" ]]; then
  CUR_VER="$("$VENV_DIR/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$CUR_VER" != "$REQUIRED_PY_MINOR" ]]; then
    echo "Existing .venv-mac uses Python $CUR_VER, recreating with $REQUIRED_PY_MINOR..."
    RECREATE_VENV=1
  fi
fi

if [[ ! -d "$VENV_DIR" || "$RECREATE_VENV" -eq 1 ]]; then
  rm -rf "$VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" - <<'PY' >/dev/null 2>&1
import tkinter
PY
then
  echo ".venv-mac Python is missing tkinter (_tkinter)." >&2
  echo "Please ensure python-tk@${REQUIRED_PY_MINOR} is installed, then rerun." >&2
  exit 1
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

bash "$ROOT/scripts/make_icns_mac.sh" || true

# Keep Playwright browsers out of site-packages; we copy them into app bundle later.
export PLAYWRIGHT_BROWSERS_PATH="$BROWSERS_CACHE_DIR"
"$VENV_DIR/bin/python" -m playwright install chromium

# Ensure PyInstaller does not pick previously bundled browsers from the package path.
PKG_BROWSERS_DIR="$VENV_DIR/lib/python${REQUIRED_PY_MINOR}/site-packages/playwright/driver/package/.local-browsers"
if [[ -d "$PKG_BROWSERS_DIR" ]]; then
  rm -rf "$PKG_BROWSERS_DIR"
fi

rm -rf dist build

ICON_PATH="$ROOT/resources/icon.icns"
if [[ ! -f "$ICON_PATH" ]]; then
  ICON_PATH="$ROOT/resources/icon.png"
fi

"$VENV_DIR/bin/python" -m PyInstaller \
  --windowed \
  --noconfirm \
  --name="$APP_NAME" \
  --icon="$ICON_PATH" \
  main.py

APP_DIR="$ROOT/dist/${APP_NAME}.app"
MACOS_DIR="$APP_DIR/Contents/MacOS"
INTERNAL_DIR="$MACOS_DIR/_internal"

cp -R "$ROOT/resources" "$MACOS_DIR/"
cp -R "$ROOT/liqi_proto" "$MACOS_DIR/"
cp "$ROOT/version" "$MACOS_DIR/version"

mkdir -p "$MACOS_DIR/models"
mkdir -p "$MACOS_DIR/chrome_ext"

MODELS_DST="$MACOS_DIR/models"
copy_models_from_dir() {
  local src_dir="$1"
  if [[ ! -d "$src_dir" ]]; then
    return
  fi
  local copied=0
  shopt -s nullglob
  for src_model in "$src_dir"/*.pth; do
    cp -f "$src_model" "$MODELS_DST/"
    copied=1
  done
  shopt -u nullglob
  if [[ "$copied" -eq 1 ]]; then
    echo "Bundled models from: $src_dir"
  fi
}

APP_SUPPORT_MODELS="$HOME/Library/Application Support/$APP_NAME/models"
HAS_APP_SUPPORT_MODELS=0
if [[ -d "$APP_SUPPORT_MODELS" ]]; then
  shopt -s nullglob
  APP_SUPPORT_PTH=("$APP_SUPPORT_MODELS"/*.pth)
  shopt -u nullglob
  if [[ ${#APP_SUPPORT_PTH[@]} -gt 0 ]]; then
    HAS_APP_SUPPORT_MODELS=1
  fi
fi

if [[ "$HAS_APP_SUPPORT_MODELS" -eq 1 ]]; then
  rm -f "$MODELS_DST"/*.pth 2>/dev/null || true
  copy_models_from_dir "$APP_SUPPORT_MODELS"
else
  copy_models_from_dir "$ROOT/models"
fi

BROWSERS_SRC="$BROWSERS_CACHE_DIR"
BROWSERS_DST="$INTERNAL_DIR/playwright/driver/package/ms-playwright"
if [[ -d "$BROWSERS_SRC" ]]; then
  mkdir -p "$BROWSERS_DST"
  rsync -a --delete "$BROWSERS_SRC"/ "$BROWSERS_DST"/
  # Playwright cache metadata folder is not needed at runtime and breaks codesign --deep.
  find "$BROWSERS_DST" -type d -name ".links" -prune -exec rm -rf {} + 2>/dev/null || true
else
  echo "WARNING: Playwright browsers not found under $BROWSERS_SRC"
fi

if command -v codesign >/dev/null 2>&1; then
  xattr -cr "$APP_DIR" || true
  codesign --force --deep --sign - --timestamp=none "$APP_DIR"
  codesign --verify --deep --strict --verbose=2 "$APP_DIR"
fi

echo "Built app: $APP_DIR"
echo "Run scripts/make_dmg_mac.sh to package DMG."
