#!/bin/bash
# Notarize DMG with Apple
set -e

DMG="$1"
APPLE_ID="${APPLE_ID:-}"
TEAM_ID="${TEAM_ID:-BD927P383Y}"
APP_PASSWORD="${APP_PASSWORD:-}"

if [ -z "$DMG" ]; then
    echo "Usage: bash scripts/notarize.sh dist/LiveTranslator-v0.0.1-macOS.dmg"
    exit 1
fi

if [ -z "$APPLE_ID" ] || [ -z "$APP_PASSWORD" ]; then
    echo "Set APPLE_ID and APP_PASSWORD environment variables"
    echo "  export APPLE_ID=your@email.com"
    echo "  export APP_PASSWORD=xxxx-xxxx-xxxx-xxxx"
    echo ""
    echo "Generate app-specific password at: appleid.apple.com"
    exit 1
fi

echo "=== Notarizing ${DMG} ==="
xcrun notarytool submit "${DMG}" \
    --apple-id "${APPLE_ID}" \
    --team-id "${TEAM_ID}" \
    --password "${APP_PASSWORD}" \
    --wait

echo "=== Stapling ==="
xcrun stapler staple "${DMG}"

echo "=== Done! ==="
