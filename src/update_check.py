"""Tell people running an older build that a new release is out.

Asks GitHub for the latest release once per launch. Never blocks the UI and
never raises: offline, rate-limited or odd responses simply mean "no update".
Turn it off with "check_for_updates": false in ~/.live-translator.json.
"""

import json
import os
import plistlib
import re
import urllib.request

REPO = "umutcetinkaya/live-translator"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"

_VERSION = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$")


def parse_version(tag):
    """'v0.2.3' or '0.2.3' → (0, 2, 3); anything else → None."""
    m = _VERSION.match((tag or "").strip())
    if not m:
        return None
    return tuple(int(part or 0) for part in m.groups())


def is_newer(latest, current):
    latest_v, current_v = parse_version(latest), parse_version(current)
    return bool(latest_v and current_v and latest_v > current_v)


def app_version(resources_dir):
    """Version from the .app's Info.plist, or None when running from source."""
    if "/Contents/Resources" not in resources_dir:
        return None
    plist = os.path.join(resources_dir.split("/Contents/Resources")[0], "Contents", "Info.plist")
    try:
        with open(plist, "rb") as f:
            return plistlib.load(f).get("CFBundleShortVersionString")
    except (OSError, plistlib.InvalidFileException):
        return None


def _fetch_json(url, headers):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def check_for_update(current, config, fetch=_fetch_json):
    """{'version': '0.2.3', 'url': ...} when a newer release exists, else None."""
    if not current or not config.get("check_for_updates", True):
        return None
    try:
        release = fetch(RELEASES_API, {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"LiveTranslator/{current}",
        })
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            return None
        tag = release.get("tag_name", "")
        if not is_newer(tag, current):
            return None
        # Build the link ourselves so the menu can only ever open this repo.
        return {"version": tag.lstrip("v"), "url": f"{RELEASES_PAGE}/tag/{tag}"}
    except Exception as e:
        print(f"[Update] check skipped: {e}")
        return None
