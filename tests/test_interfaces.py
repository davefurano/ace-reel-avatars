import inspect, pytest
from ace_reel.contracts.interfaces import AceClient, RenderTarget, MusicSource, Track

def test_interfaces_are_abstract():
    for cls in (AceClient, RenderTarget, MusicSource):
        with pytest.raises(TypeError):
            cls()

def test_track_carries_metadata():
    t = Track(id="abc", title="Song", duration_s=180, audio_url="https://x/y.mp3", bpm=None)
    assert t.id == "abc" and t.bpm is None

def test_aceclient_stream_is_the_contract():
    assert "stream" in {n for n, _ in inspect.getmembers(AceClient, inspect.isfunction)}
