import pytest
from providers.base import RealtimeProvider

def test_realtime_provider_is_abstract():
    with pytest.raises(TypeError):
        RealtimeProvider()

def test_must_implement_methods():
    class Incomplete(RealtimeProvider):
        def start(self, on_translation, on_source): ...
    with pytest.raises(TypeError):
        Incomplete()
