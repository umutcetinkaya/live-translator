"""STT hata sınıflandırma testleri.

Canlı ölçümde (2026-07-28) sessizlik sırasında şu görüldü:
  kAFAssistantErrorDomain code=1110 "No speech detected"
Kod bunu ölümcül hata sanıp 0.3 sn sonra yeniden başlatıyordu; sessizlik
sürdüğü için döngü kendini besliyor ve saniyede onlarca restart oluyordu.
1110 bir arıza değil, normal "bu seste konuşma yok" bildirimi.
"""

import sys
from unittest.mock import MagicMock

_NATIVE = ("objc", "Speech", "Foundation")
_INJECTED = [m for m in _NATIVE if m not in sys.modules]
for m in _INJECTED:
    sys.modules[m] = MagicMock()

import pytest
import speech_recognizer as sr


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    for m in _INJECTED:
        sys.modules.pop(m, None)


def _err(domain="kAFAssistantErrorDomain", code=1110):
    e = MagicMock()
    e.domain.return_value = domain
    e.code.return_value = code
    return e


def test_no_speech_is_not_fatal():
    """1110 sessizliğin normal sonucu — restart tetiklememeli."""
    assert sr._is_fatal_error(_err(code=1110)) is False


def test_speech_timeout_is_not_fatal():
    """1107 de aynı aileden: konuşma beklenirken zaman aşımı."""
    assert sr._is_fatal_error(_err(code=1107)) is False


def test_unknown_error_is_fatal():
    """Tanımadığımız hata gerçek arıza sayılmalı — restart gerekir."""
    assert sr._is_fatal_error(_err(code=203)) is True


def test_other_domain_is_fatal():
    assert sr._is_fatal_error(_err(domain="NSURLErrorDomain", code=1110)) is True


def test_none_error_is_not_fatal():
    assert sr._is_fatal_error(None) is False


def test_unreadable_error_treated_as_fatal():
    """domain()/code() patlarsa güvenli taraf: gerçek arıza varsay."""
    bad = MagicMock()
    bad.domain.side_effect = RuntimeError("boom")
    assert sr._is_fatal_error(bad) is True


def test_restart_backoff_grows():
    """Arka arkaya restart'ta bekleme artmalı — döngü CPU yakmasın."""
    delays = [sr._restart_delay(i) for i in range(6)]
    assert delays == sorted(delays), delays
    assert delays[0] < delays[-1]


def test_restart_backoff_is_capped():
    """Geri çekilme sınırsız büyümemeli; kurtarma makul sürede olmalı."""
    assert sr._restart_delay(100) <= sr.MAX_RESTART_DELAY


def test_first_restart_is_prompt():
    """İlk yeniden deneme hızlı olmalı — gerçek arızada kullanıcı beklemesin."""
    assert sr._restart_delay(0) <= 0.5
