import pytest
from ace_reel.motion.beat import BeatResult
from ace_reel.motion.planner import plan_dance


def test_raises_on_empty_clips():
    with pytest.raises(ValueError):
        plan_dance(BeatResult(120, [0.0, 0.5, 1.0]), clips=[], beats_per_bar=4)


def test_plans_one_clip_cue_per_bar():
    beats = BeatResult(bpm=120, beat_times_s=[0.0,0.5,1.0,1.5,2.0,2.5,3.0,3.5])
    cues = plan_dance(beats, clips=["sway", "step"], beats_per_bar=4)
    assert len(cues) == 2
    assert cues[0].start_s == 0.0 and cues[1].start_s == 2.0
    assert cues[0].clip_name in ("sway", "step")
    assert 0.0 <= cues[0].energy <= 1.0


def test_energy_scales_with_tempo():
    slow = plan_dance(BeatResult(60, [0,1,2,3,4]), clips=["a"], beats_per_bar=4)
    fast = plan_dance(BeatResult(160, [0,0.375,0.75,1.125,1.5]), clips=["a"], beats_per_bar=4)
    assert fast[0].energy > slow[0].energy
