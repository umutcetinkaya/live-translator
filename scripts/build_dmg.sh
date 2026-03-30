#!/bin/bash
# Create DMG installer for Live Translator
set -e

VERSION="${1:-0.0.1}"
APP_NAME="Live Translator"
DMG_NAME="LiveTranslator-v${VERSION}-macOS"
DMG_DIR="dist/dmg"

echo "=== Creating DMG: ${DMG_NAME}.dmg ==="

# Build .app first if not exists
if [ ! -d "dist/${APP_NAME}.app" ]; then
    bash scripts/build_app.sh "${VERSION}"
fi

# Prepare DMG contents
rm -rf "${DMG_DIR}"
mkdir -p "${DMG_DIR}"
cp -r "dist/${APP_NAME}.app" "${DMG_DIR}/"

# Create symlink to Applications
ln -s /Applications "${DMG_DIR}/Applications"

# Create DMG
hdiutil create -volname "${APP_NAME}" \
    -srcfolder "${DMG_DIR}" \
    -ov -format UDZO \
    "dist/${DMG_NAME}.dmg"

# Clean temp
rm -rf "${DMG_DIR}"

echo ""
echo "=== Created: dist/${DMG_NAME}.dmg ==="
echo "Size: $(du -h "dist/${DMG_NAME}.dmg" | cut -f1)"
