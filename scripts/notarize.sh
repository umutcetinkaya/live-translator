#!/bin/bash
# Notarize and staple a DMG so macOS opens the app without a warning.
#
# Credentials come from a notarytool keychain profile, created once with:
#   xcrun notarytool store-credentials "livetranslator-notary" \
#       --apple-id you@example.com --team-id BD927P383Y
# (the password is an app-specific password from account.apple.com).
# Credentials are only read from the keychain, never from the environment or
# the command line. Set NOTARY_PROFILE to use another profile name.
set -e

DMG="$1"
NOTARY_PROFILE="${NOTARY_PROFILE:-livetranslator-notary}"

if [ -z "$DMG" ] || [ ! -f "$DMG" ]; then
    echo "Usage: bash scripts/notarize.sh dist/LiveTranslator-v<version>-macOS.dmg"
    exit 1
fi

AUTH=(--keychain-profile "${NOTARY_PROFILE}")

echo "=== Notarizing ${DMG} ==="
xcrun notarytool submit "${DMG}" "${AUTH[@]}" --wait --output-format json > dist/notarize.json
STATUS="$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' dist/notarize.json)"
SUB_ID="$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' dist/notarize.json)"
echo "    Status: ${STATUS} (${SUB_ID})"

if [ "${STATUS}" != "Accepted" ]; then
    echo "=== Notarization failed; Apple's log follows ==="
    xcrun notarytool log "${SUB_ID}" "${AUTH[@]}"
    exit 1
fi

echo "=== Stapling ==="
xcrun stapler staple "${DMG}"
xcrun stapler validate "${DMG}"

echo "=== Gatekeeper check ==="
spctl -a -t open --context context:primary-signature -v "${DMG}"

echo "=== Done: ${DMG} ==="
