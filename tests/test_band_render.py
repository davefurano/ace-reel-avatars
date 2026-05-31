# tests/test_band_render.py
import pytest, sys
from ace_reel.band.performance import BandPerformance
from ace_reel.band.roster import Role, Member, Band
from ace_reel.contracts.interfaces import Track
from ace_reel.contracts.frame import AnimationFrame
from ace_reel.motion.planner import ClipCue
from ace_reel.render.band_base import BandRenderTarget, NullBandRenderTarget
from ace_reel.render.unreal_band import UnrealBandRenderTarget


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


def test_null_band_target_records_members_audio_frames_close():
    v = Member("Claire", Role.VOCALS, ())
    g = Member("Mark", Role.GUITAR, ("g1",))
    arrangement = {g: [ClipCue("g1", 0.0, 0.5)]}
    perf = BandPerformance(
        track=Track("t1", "S", 10, "https://x/a.mp3"),
        audio_pcm=b"PCMPCM",
        vocalist=v,
        vocal_frames=[
            AnimationFrame(timestamp_s=0.0, blendshapes={"JawOpen": 0.5}, emotions={}, body_pose=None),
            AnimationFrame(timestamp_s=0.03, blendshapes={"JawOpen": 0.1}, emotions={}, body_pose=None),
        ],
        instrument_arrangement=arrangement,
    )
    t = NullBandRenderTarget()
    t.run(perf)
    assert t.opened_with == ([v, g], len(b"PCMPCM"), arrangement)
    assert [f.timestamp_s for f in t.vocal_received] == [0.0, 0.03]
    assert t.closed is True


def test_unreal_band_is_a_band_render_target_and_preflight_rejects_off_windows():
    assert issubclass(UnrealBandRenderTarget, BandRenderTarget)
    t = UnrealBandRenderTarget()
    if sys.platform == "win32":
        pytest.skip("preflight only rejects off-Windows")
    with pytest.raises(NotImplementedError) as e:
        t.preflight()
    assert "Windows" in str(e.value) and "setup-reel-engine" in str(e.value)
