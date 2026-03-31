#!/bin/bash
# Build Live Translator.app bundle for macOS
set -e

APP_NAME="Live Translator"
APP_DIR="dist/${APP_NAME}.app"
VERSION="${1:-0.0.1}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Building ${APP_NAME} v${VERSION} ==="
cd "$PROJECT_DIR"

rm -rf "dist/${APP_NAME}.app"
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"
mkdir -p "${APP_DIR}/Contents/Resources/models"
mkdir -p "${APP_DIR}/Contents/Resources/src"
mkdir -p "${APP_DIR}/Contents/Resources/scripts"

# Icon
if [ -f "assets/icon.icns" ]; then
    cp assets/icon.icns "${APP_DIR}/Contents/Resources/AppIcon.icns"
    ICON_LINE="
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>"
else
    ICON_LINE=""
fi

# Info.plist
cat > "${APP_DIR}/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key><string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key><string>com.livetranslator.app</string>
    <key>CFBundleVersion</key><string>${VERSION}</string>
    <key>CFBundleShortVersionString</key><string>${VERSION}</string>
    <key>CFBundleExecutable</key><string>launcher</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>LSMinimumSystemVersion</key><string>13.0</string>
    <key>LSUIElement</key><true/>
    ${ICON_LINE}
    <key>NSMicrophoneUsageDescription</key>
    <string>Live Translator needs microphone access for speech recognition.</string>
    <key>NSSpeechRecognitionUsageDescription</key>
    <string>Live Translator uses speech recognition to transcribe audio.</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2025 Umut Çetinkaya — umutcetinkaya.com</string>
</dict>
</plist>
PLIST

# Copy source
cp main.py "${APP_DIR}/Contents/Resources/"
cp -r src/ "${APP_DIR}/Contents/Resources/src/"
cp requirements.txt "${APP_DIR}/Contents/Resources/"
cp scripts/download_models.sh "${APP_DIR}/Contents/Resources/scripts/"

# Compile setup wizard if needed
if [ ! -f scripts/setup_wizard ] || [ scripts/setup_wizard.swift -nt scripts/setup_wizard ]; then
    echo "  Compiling setup wizard..."
    swiftc -O -o scripts/setup_wizard scripts/setup_wizard.swift -framework Cocoa
fi
cp scripts/setup_wizard "${APP_DIR}/Contents/Resources/scripts/"

# Copy models if exist
if ls models/*.onnx 1>/dev/null 2>&1; then
    cp models/*.onnx models/*.onnx.json "${APP_DIR}/Contents/Resources/models/" 2>/dev/null || true
    echo "  Models included"
fi

# Launcher — runs setup wizard if needed, then launches app
cat > "${APP_DIR}/Contents/MacOS/launcher" << 'LAUNCHER'
#!/bin/bash

DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
CONFIG="${HOME}/.live-translator.json"
SUPPORT="${HOME}/Library/Application Support/LiveTranslator"
VENV="${SUPPORT}/venv"
LOG="${HOME}/Library/Logs/LiveTranslator.log"
MARKER="/tmp/.livetranslator_launch"

mkdir -p "${SUPPORT}" 2>/dev/null

HAS_KEY=false
HAS_VENV=false

if [ -f "${CONFIG}" ]; then
    if grep -q '"openai_api_key"' "${CONFIG}" 2>/dev/null; then
        if ! grep -q '"openai_api_key": ""' "${CONFIG}" 2>/dev/null; then
            HAS_KEY=true
        fi
    fi
fi

if [ -f "${VENV}/bin/python" ]; then
    HAS_VENV=true
fi

# Need setup?
if [ "${HAS_KEY}" = false ] || [ "${HAS_VENV}" = false ]; then
    rm -f "${MARKER}" 2>/dev/null
    "${DIR}/scripts/setup_wizard" "${DIR}" 2>>"${LOG}"

    if [ ! -f "${MARKER}" ]; then
        exit 0
    fi
    rm -f "${MARKER}" 2>/dev/null
fi

# Launch
cd "${DIR}"
exec "${VENV}/bin/python" "${DIR}/main.py" 2>>"${LOG}"
LAUNCHER

# Move bash launcher to Resources (not MacOS — so codesign works)
mv "${APP_DIR}/Contents/MacOS/launcher" "${APP_DIR}/Contents/Resources/launcher.sh"
chmod +x "${APP_DIR}/Contents/Resources/launcher.sh"

# Compile native C launcher
cc -O2 -o "${APP_DIR}/Contents/MacOS/launcher" "${PROJECT_DIR}/scripts/launcher.c"


# Code sign with Developer ID
SIGN_ID="${SIGN_ID:-Developer ID Application: Umut Cetinkaya (BD927P383Y)}"

# Sign binaries individually (inside out)
codesign --force --options runtime --sign "${SIGN_ID}" "${APP_DIR}/Contents/Resources/scripts/setup_wizard" 2>/dev/null
codesign --force --options runtime --sign "${SIGN_ID}" "${APP_DIR}/Contents/MacOS/launcher" 2>/dev/null

# Sign the bundle
codesign --force --options runtime --sign "${SIGN_ID}" "${APP_DIR}" 2>/dev/null && \
    echo "  Code signed: ${SIGN_ID}" || \
    echo "  WARNING: signing failed"

# Remove quarantine
xattr -cr "${APP_DIR}" 2>/dev/null

echo "=== Built: ${APP_DIR} ==="
