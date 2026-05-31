# tests/test_band_orchestrator.py
from ace_reel.band.orchestrator import BandOrchestrator
from ace_reel.band.roster import Role, Member, Band
from ace_reel.motion.beat import BeatResult
from ace_reel.render.band_base import NullBandRenderTarget
from tests.fakes import FakeMusicSource, FakeAceClient

def _band():
    return Band("House", (
        Member("Claire", Role.VOCALS, ()),
        Member("Mark", Role.GUITAR, ("g1",)),
        Member("Beat", Role.DRUMS, ("kick",)),
    ))

def test_band_perform_wires_music_beats_ace_into_band_render(monkeypatch):
    import ace_reel.band.orchestrator as bo
    monkeypatch.setattr(bo, "to_pcm_16k_mono_bytes", lambda src: b"PCM16K")
    monkeypatch.setattr(bo, "detect_beats", lambda path: BeatResult(120, [i * 0.5 for i in range(8)]))
    target = NullBandRenderTarget()
    BandOrchestrator(FakeMusicSource(), FakeAceClient(), target).perform("t1", _band())

    members, audio_len, arrangement = target.opened_with
    assert {m.avatar for m in members} == {"Claire", "Mark", "Beat"}
    assert audio_len == len(b"PCM16K")
    assert [f.timestamp_s for f in target.vocal_received] == [0.0, 0.033]
    assert {m.avatar for m in arrangement} == {"Mark", "Beat"}
    assert target.closed is True
