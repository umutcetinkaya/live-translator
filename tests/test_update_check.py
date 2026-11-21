"""Update check: tell people running an old build that a new release exists.

494 people downloaded 0.1.0 before the app became free; without a check they
never hear about it. The check asks GitHub for the latest release once per
launch, never blocks the UI, and stays silent on any error.
"""

import plistlib

from update_check import (RELEASES_API, RELEASES_PAGE, app_version, check_for_update,
                          is_newer, parse_version)


def test_parse_version():
    assert parse_version("v0.2.3") == (0, 2, 3)
    assert parse_version("0.10.0") == (0, 10, 0)
    assert parse_version("v1.2") == (1, 2, 0)
    assert parse_version("nightly") is None
    assert parse_version("") is None
    assert parse_version(None) is None


def test_is_newer_compares_numerically():
    assert is_newer("v0.2.3", "0.2.2")
    assert is_newer("v0.10.0", "0.9.9")
    assert not is_newer("v0.2.2", "0.2.2")
    assert not is_newer("v0.2.1", "0.2.2")
    assert not is_newer("garbage", "0.2.2")
    assert not is_newer("v0.2.3", None)


def _bundle(tmp_path, version):
    contents = tmp_path / "Live Translator.app" / "Contents"
    resources = contents / "Resources"
    resources.mkdir(parents=True)
    with open(contents / "Info.plist", "wb") as f:
        plistlib.dump({"CFBundleShortVersionString": version}, f)
    return str(resources)


def test_app_version_read_from_bundle(tmp_path):
    assert app_version(_bundle(tmp_path, "0.2.2")) == "0.2.2"


def test_app_version_none_when_running_from_source(tmp_path):
    assert app_version(str(tmp_path)) is None


def _release(tag="v0.2.3", **extra):
    return {"tag_name": tag, "html_url": f"{RELEASES_PAGE}/tag/{tag}",
            "draft": False, "prerelease": False, **extra}


def test_newer_release_is_reported():
    calls = []

    def fetch(url, headers):
        calls.append((url, headers))
        return _release()

    update = check_for_update("0.2.2", {}, fetch=fetch)
    assert update == {"version": "0.2.3", "url": f"{RELEASES_PAGE}/tag/v0.2.3"}
    url, headers = calls[0]
    assert url == RELEASES_API == "https://api.github.com/repos/umutcetinkaya/live-translator/releases/latest"
    assert headers["User-Agent"] == "LiveTranslator/0.2.2"


def test_same_or_older_release_is_ignored():
    assert check_for_update("0.2.3", {}, fetch=lambda u, h: _release("v0.2.3")) is None
    assert check_for_update("0.3.0", {}, fetch=lambda u, h: _release("v0.2.3")) is None


def test_prerelease_and_draft_are_ignored():
    assert check_for_update("0.2.2", {}, fetch=lambda u, h: _release(prerelease=True)) is None
    assert check_for_update("0.2.2", {}, fetch=lambda u, h: _release(draft=True)) is None


def test_errors_are_silent():
    def boom(url, headers):
        raise OSError("offline")

    assert check_for_update("0.2.2", {}, fetch=boom) is None
    assert check_for_update("0.2.2", {}, fetch=lambda u, h: {"message": "rate limited"}) is None
    assert check_for_update("0.2.2", {}, fetch=lambda u, h: None) is None


def test_link_always_points_at_this_repo():
    # A tampered response must not turn the menu item into a link elsewhere.
    update = check_for_update("0.2.2", {}, fetch=lambda u, h: _release(html_url="https://evil.example/x"))
    assert update["url"] == f"{RELEASES_PAGE}/tag/v0.2.3"


def test_no_check_when_running_from_source():
    called = []
    assert check_for_update(None, {}, fetch=lambda u, h: called.append(1)) is None
    assert called == []


def test_can_be_turned_off():
    called = []
    assert check_for_update("0.2.2", {"check_for_updates": False},
                            fetch=lambda u, h: called.append(1)) is None
    assert called == []


def test_on_by_default():
    from config import DEFAULTS
    assert DEFAULTS["check_for_updates"] is True
