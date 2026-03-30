#!/bin/bash
# Build Live Translator.app bundle for macOS
set -e

APP_NAME="Live Translator"
APP_DIR="dist/${APP_NAME}.app"
VERSION="${1:-0.0.1}"

echo "=== Building ${APP_NAME} v${VERSION} ==="

# Clean
rm -rf dist/
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"
mkdir -p "${APP_DIR}/Contents/Resources/models"

# Info.plist
cat > "${APP_DIR}/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Live Translator</string>
    <key>CFBundleDisplayName</key>
    <string>Live Translator</string>
    <key>CFBundleIdentifier</key>
    <string>com.livetranslator.app</string>
    <key>CFBundleVersion</key>
    <string>VERSION_PLACEHOLDER</string>
    <key>CFBundleShortVersionString</key>
    <string>VERSION_PLACEHOLDER</string>
    <key>CFBundleExecutable</key>
    <string>run.sh</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Live Translator needs microphone access for speech recognition.</string>
    <key>NSSpeechRecognitionUsageDescription</key>
    <string>Live Translator uses speech recognition to transcribe audio.</string>
    <key>NSScreenCaptureUsageDescription</key>
    <string>Live Translator captures system audio to translate speech.</string>
</dict>
</plist>
PLIST

# Replace version
sed -i '' "s/VERSION_PLACEHOLDER/${VERSION}/g" "${APP_DIR}/Contents/Info.plist"

# Copy source
cp main.py "${APP_DIR}/Contents/Resources/"
cp -r src/ "${APP_DIR}/Contents/Resources/src/"
cp requirements.txt "${APP_DIR}/Contents/Resources/"
cp -r scripts/ "${APP_DIR}/Contents/Resources/scripts/"

# Copy models if they exist
if ls models/*.onnx 1>/dev/null 2>&1; then
    cp models/*.onnx models/*.onnx.json "${APP_DIR}/Contents/Resources/models/" 2>/dev/null || true
    echo "  Models included"
else
    echo "  No models found (TTS will use OpenAI or download on first use)"
fi

# Launcher script
cat > "${APP_DIR}/Contents/MacOS/run.sh" << 'LAUNCHER'
#!/bin/bash
DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
CONFIG="$HOME/.live-translator.json"

# Check for OpenAI API key
if [ ! -f "$CONFIG" ] || ! grep -q "openai_api_key" "$CONFIG" 2>/dev/null || grep -q '"openai_api_key": ""' "$CONFIG" 2>/dev/null; then
    # Prompt for API key
    KEY=$(osascript -e 'display dialog "Enter your OpenAI API Key to use Live Translator:" default answer "" with title "Live Translator Setup" with icon note buttons {"Cancel", "OK"} default button "OK"' -e 'text returned of result' 2>/dev/null)

    if [ -z "$KEY" ]; then
        osascript -e 'display alert "Live Translator" message "OpenAI API key is required. The app will now exit." as critical buttons {"OK"}'
        exit 1
    fi

    # Save config
    cat > "$CONFIG" << EOF
{
  "openai_api_key": "${KEY}",
  "source_locale": "en-US",
  "target_lang": "tr",
  "model": "gpt-4o-mini",
  "tts_provider": "piper",
  "tts_voice": "nova",
  "tts_speed": 1.0
}
EOF
    echo "Config saved to $CONFIG"
fi

# Setup venv if needed
if [ ! -d "$DIR/.venv" ]; then
    osascript -e 'display notification "Installing dependencies, please wait..." with title "Live Translator"'
    python3 -m venv "$DIR/.venv"
    "$DIR/.venv/bin/pip" install -r "$DIR/requirements.txt" -q

    # Download TTS models
    if [ -f "$DIR/scripts/download_models.sh" ]; then
        bash "$DIR/scripts/download_models.sh"
    fi
fi

# Run
cd "$DIR"
exec "$DIR/.venv/bin/python" "$DIR/main.py"
LAUNCHER

chmod +x "${APP_DIR}/Contents/MacOS/run.sh"

echo "=== Built: ${APP_DIR} ==="
echo ""
echo "To create DMG: bash scripts/build_dmg.sh ${VERSION}"
