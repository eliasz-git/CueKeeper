#!/bin/bash
# build_app.sh — Build a self-contained, double-clickable CueKeeper Mac .app
#
# Produces: CueKeeper.app  (in the project root)
#
# The app bundles its own Python venv + dependencies, so the operator only
# needs to double-click it. On first launch it:
#   * auto-generates a CUEKEEPER_TOKEN
#   * stores show data in ~/Library/Application Support/CueKeeper
#   * starts uvicorn on http://0.0.0.0:8000
#   * opens a NATIVE macOS window (WKWebView via PyObjC) — NOT a browser tab
#   * shows the token in a notification (paste it into the UI's token field)
#
# Usage: ./mac_app/build_app.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="CueKeeper.app"
APP_PATH="${PROJECT_DIR}/${APP_NAME}"
VERSION="0.1.0"
PORT="${CUEKEEPER_PORT:-8000}"

# Use the existing uv-managed Python 3.11 (has fastapi/uvicorn already)
BUILD_PY="${PROJECT_DIR}/.venv/bin/python"
if [ ! -x "$BUILD_PY" ]; then
  echo "ERROR: $BUILD_PY not found. Run from the CueKeeper project with .venv present."
  exit 1
fi

echo "==> Removing old ${APP_NAME}..."
rm -rf "$APP_PATH"

# --- App bundle directory structure ---
RESOURCES="${APP_PATH}/Contents/Resources"
MACOS="${APP_PATH}/Contents/MacOS"
mkdir -p "$MACOS" "$RESOURCES"

# --- Bundled Python venv ---
echo "==> Creating bundled Python venv..."
APP_VENV="${RESOURCES}/venv"
"$BUILD_PY" -m venv "$APP_VENV"

echo "==> Bootstrapping pip into the app venv..."
"${APP_VENV}/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true

echo "==> Installing Python dependencies into the app..."
"${APP_VENV}/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
"${APP_VENV}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"
"${APP_VENV}/bin/pip" install pyobjc-framework-Cocoa pyobjc-framework-WebKit

# --- App source (static files served by the server) ---
echo "==> Copying application source..."
APP_SRC="${RESOURCES}/app"
mkdir -p "$APP_SRC"
cp -r "${PROJECT_DIR}/src" "$APP_SRC/src"
cp -r "${PROJECT_DIR}/static" "$APP_SRC/static"
cp "${PROJECT_DIR}/requirements.txt" "$APP_SRC/requirements.txt"
cp "${PROJECT_DIR}/mac_app/CueKeeperApp.py" "$APP_SRC/CueKeeperApp.py"

# --- App icon (optional) ---
ICON_PLIST=""
if [ -f "${PROJECT_DIR}/mac_app/CueKeeper.icns" ]; then
  cp "${PROJECT_DIR}/mac_app/CueKeeper.icns" "${RESOURCES}/CueKeeper.icns"
  ICON_PLIST="
<key>CFBundleIconFile</key>
<string>CueKeeper</string>"
fi

# --- Info.plist ---
echo "==> Writing Info.plist..."
cat > "${APP_PATH}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
<key>CFBundleExecutable</key>
<string>CueKeeperLauncher</string>
${ICON_PLIST}
<key>CFBundleIdentifier</key>
<string>com.cuekeeper.app</string>
<key>CFBundleName</key>
<string>CueKeeper</string>
<key>CFBundleDisplayName</key>
<string>CueKeeper</string>
<key>CFBundleVersion</key>
<string>${VERSION}</string>
<key>CFBundleShortVersionString</key>
<string>${VERSION}</string>
<key>CFBundlePackageType</key>
<string>APPL</string>
<key>LSHighResolutionCapable</key>
<true/>
<key>NSHumanReadableCopyright</key>
<string>Copyright © Elias. MIT License.</string>
<key>NSRequiresAquaSystemAppearance</key>
<false/>
</dict>
</plist>
PLIST

# --- Launcher executable (starts uvicorn, then shows the native window) ---
echo "==> Writing launcher..."
cat > "${MACOS}/CueKeeperLauncher" <<LAUNCHER
#!/bin/bash
# CueKeeperLauncher — entry point for CueKeeper.app
set -u

# Resolve the app bundle directories from this script's location.
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
RESOURCES_DIR="\$(cd "\${SCRIPT_DIR}/../Resources" && pwd)"
APP_DIR="\${RESOURCES_DIR}/app"
VENV_PYTHON="\${RESOURCES_DIR}/venv/bin/python"

# Make sure standard bins are on PATH (LaunchServices can give a thin PATH).
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:\${PATH}"

# Show data lives in Application Support so it survives app updates.
DATA_DIR="\${HOME}/Library/Application Support/CueKeeper"
AUDIO_DIR="\${DATA_DIR}/audio"
mkdir -p "\${DATA_DIR}" "\${AUDIO_DIR}"

PORT="${PORT}"

# Auto-generate a token on first launch; reuse it thereafter so cues persist.
TOKEN_FILE="\${DATA_DIR}/token.txt"
if [ ! -f "\${TOKEN_FILE}" ]; then
  TOKEN="\$(\${VENV_PYTHON} -c "import secrets; print(secrets.token_urlsafe(24))")"
  echo "\${TOKEN}" > "\${TOKEN_FILE}"
else
  TOKEN=\$(cat "\${TOKEN_FILE}")
fi

export CUEKEEPER_DATA="\${DATA_DIR}/data.json"
export CUEKEEPER_AUDIO="\${AUDIO_DIR}"
export CUEKEEPER_TOKEN="\${TOKEN}"
export CUEKEEPER_AUTH_REQUIRED="true"

SERVER_LOG="\${DATA_DIR}/server.log"

# Start uvicorn in the background.
cd "\${APP_DIR}"
"\${VENV_PYTHON}" -m uvicorn src.main:app --host 0.0.0.0 --port "\${PORT}" > "\${SERVER_LOG}" 2>&1 &
SERVER_PID=\$!

# Ensure the server stops when the app is quit.
cleanup() {
  kill "\${SERVER_PID}" 2>/dev/null || true
  wait "\${SERVER_PID}" 2>/dev/null || true
}
trap cleanup EXIT TERM INT

# Wait for the server to become ready.
READY=0
for i in \$(seq 1 60); do
  if curl -sf "http://127.0.0.1:\${PORT}/healthz" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 0.5
done

if [ "\${READY}" -eq 1 ]; then
  # Show the native app window (NOT a browser tab).
  "\${VENV_PYTHON}" "\${APP_DIR}/CueKeeperApp.py" &
  GUI_PID=\$!
  wait "\${GUI_PID}"
  osascript -e "display notification \"CueKeeper stopped.\" with title \"CueKeeper\" sound name \"Ping\""
else
  osascript -e "display notification \"CueKeeper failed to start. See \${SERVER_LOG}\" with title \"CueKeeper\" sound name \"Basso\""
  exit 1
fi
LAUNCHER
chmod +x "${MACOS}/CueKeeperLauncher"

echo "==> Done: ${APP_PATH}"
echo "    Double-click CueKeeper.app to launch (native window, not a browser tab)."
echo "    Show data: ${HOME}/Library/Application Support/CueKeeper"
echo "    Token is auto-generated and shown in a notification on first launch."
