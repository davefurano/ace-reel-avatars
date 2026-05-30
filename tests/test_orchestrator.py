from ace_reel.orchestrator import Orchestrator
from ace_reel.render.base import NullRenderTarget
from tests.fakes import FakeMusicSource, FakeAceClient

def test_perform_pipes_music_through_ace_into_render(monkeypatch):
    import ace_reel.orchestrator as orch
    monkeypatch.setattr(orch, "to_pcm_16k_mono_bytes", lambda src: b"PCM16K")
    target = NullRenderTarget()
    Orchestrator(FakeMusicSource(), FakeAceClient(), target).perform("track1", "Avatar_Claire")
    assert target.opened_with == ("Avatar_Claire", len(b"PCM16K"))
    assert [f.timestamp_s for f in target.received] == [0.0, 0.033]
    assert target.closed is True
