"""Languages: Turkish, Dutch and Polish as spoken languages (issue #11).

Turkish was only a target. Apple speech recognition and TranslateGemma both
handle Turkish, Dutch and Polish, so they can be the language being spoken
too, and Dutch and Polish become targets as well.
"""

from config import LANGUAGE_NAMES, SOURCE_LANGUAGES, TARGET_LANGUAGES
from providers.local import _language_code
from providers.piper import PIPER_PATHS, PIPER_VOICES


def test_new_source_languages():
    assert SOURCE_LANGUAGES["Turkish"] == "tr-TR"
    assert SOURCE_LANGUAGES["Dutch"] == "nl-NL"
    assert SOURCE_LANGUAGES["Polish"] == "pl-PL"


def test_new_target_languages_in_their_own_names():
    assert TARGET_LANGUAGES["Nederlands"] == "nl"
    assert TARGET_LANGUAGES["Polski"] == "pl"
    assert LANGUAGE_NAMES["nl"] == "Dutch"
    assert LANGUAGE_NAMES["pl"] == "Polish"


def test_every_target_has_a_prompt_name():
    assert set(TARGET_LANGUAGES.values()) <= set(LANGUAGE_NAMES)


def test_translategemma_codes_for_new_languages():
    assert _language_code("tr-TR") == "tr"
    assert _language_code("nl-NL") == "nl"
    assert _language_code("pl-PL") == "pl"
    assert _language_code("Dutch") == "nl"
    assert _language_code("Polish") == "pl"


def test_piper_voices_for_new_targets():
    assert PIPER_VOICES["nl"] == "nl_NL-mls-medium"
    assert PIPER_PATHS["nl"] == "nl/nl_NL/mls/medium"
    assert PIPER_VOICES["pl"] == "pl_PL-gosia-medium"
    assert PIPER_PATHS["pl"] == "pl/pl_PL/gosia/medium"
