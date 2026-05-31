# tests/test_band_render.py
from ace_reel.band.performance import BandPerformance
from ace_reel.band.roster import Role, Member
from ace_reel.contracts.interfaces import Track
from ace_reel.contracts.frame import AnimationFrame


def _vocal_frames():
    yield AnimationFrame(timestamp_s=0.0, blendshapes={"JawOpen": 0.5}, emotions={}, body_pose=None)


def test_band_performance_holds_its_parts():
    v = Member("Claire", Role.VOCALS, ())
    perf = BandPerformance(
        track=Track("t1", "Song", 200, "https://x/a.mp3"),
        audio_pcm=b"PCM",
        vocalist=v,
        vocal_frames=_vocal_frames(),
        instrument_arrangement={},
    )
    assert perf.vocalist is v
    assert perf.audio_pcm == b"PCM"
    assert list(perf.vocal_frames)[0].blendshapes["JawOpen"] == 0.5
