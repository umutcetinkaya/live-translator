#!/bin/bash
# Create a polished DMG installer for Live Translator
set -e

VERSION="${1:-0.0.1}"
APP_NAME="Live Translator"
DMG_NAME="LiveTranslator-v${VERSION}-macOS"
DMG_DIR="dist/dmg"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_DIR"

echo "=== Creating ${DMG_NAME}.dmg ==="

# Build .app first
bash scripts/build_app.sh "${VERSION}"

# Prepare DMG contents
rm -rf "${DMG_DIR}"
mkdir -p "${DMG_DIR}"
cp -r "dist/${APP_NAME}.app" "${DMG_DIR}/"
ln -s /Applications "${DMG_DIR}/Applications"

# Create temp DMG (read-write)
hdiutil create -volname "${APP_NAME}" \
    -srcfolder "${DMG_DIR}" \
    -ov -format UDRW \
    "dist/${DMG_NAME}-temp.dmg" > /dev/null

# Mount and customize
MOUNT_DIR=$(hdiutil attach "dist/${DMG_NAME}-temp.dmg" -readwrite -noverify | grep "/Volumes" | sed 's/.*\(\/Volumes\/.*\)/\1/' | tr -d '\t')

if [ -n "$MOUNT_DIR" ]; then
    # Set DMG window properties via AppleScript
    osascript << APPLESCRIPT
        tell application "Finder"
            tell disk "${APP_NAME}"
                open
                set current view of container window to icon view
                set toolbar visible of container window to false
                set statusbar visible of container window to false
                set bounds of container window to {200, 120, 860, 520}
                set viewOptions to the icon view options of container window
                set arrangement of viewOptions to not arranged
                set icon size of viewOptions to 100
                set position of item "${APP_NAME}.app" of container window to {160, 180}
                set position of item "Applications" of container window to {500, 180}
                close
                open
                update without registering applications
            end tell
        end tell
APPLESCRIPT

    # Set volume icon
    if [ -f "assets/icon.icns" ]; then
        cp assets/icon.icns "${MOUNT_DIR}/.VolumeIcon.icns"
        SetFile -c icnC "${MOUNT_DIR}/.VolumeIcon.icns" 2>/dev/null || true
        SetFile -a C "${MOUNT_DIR}" 2>/dev/null || true
    fi

    # Remove quarantine flags
    xattr -cr "${MOUNT_DIR}/${APP_NAME}.app" 2>/dev/null

    sync
    hdiutil detach "$MOUNT_DIR" -quiet
fi

# Convert to compressed DMG
hdiutil convert "dist/${DMG_NAME}-temp.dmg" \
    -format UDZO -imagekey zlib-level=9 \
    -o "dist/${DMG_NAME}.dmg" > /dev/null

rm -f "dist/${DMG_NAME}-temp.dmg"
rm -rf "${DMG_DIR}"

echo "=== Created: dist/${DMG_NAME}.dmg ==="
echo "    Size: $(du -h "dist/${DMG_NAME}.dmg" | cut -f1)"
