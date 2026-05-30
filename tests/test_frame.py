import pytest
from pydantic import ValidationError
from ace_reel.contracts.frame import AnimationFrame, ARKIT_52, EMOTIONS

def test_frame_holds_arkit_blendshapes_emotions_and_timestamp():
    bs = {name: 0.0 for name in ARKIT_52}
    bs["JawOpen"] = 0.8
    emo = {name: 0.0 for name in EMOTIONS}
    emo["joy"] = 0.5
    f = AnimationFrame(timestamp_s=0.033, blendshapes=bs, emotions=emo, body_pose=None)
    assert f.timestamp_s == pytest.approx(0.033)
    assert f.blendshapes["JawOpen"] == pytest.approx(0.8)
    assert f.emotions["joy"] == pytest.approx(0.5)
    assert f.body_pose is None

def test_frame_rejects_unknown_blendshape():
    bs = {"NotARealShape": 0.5}
    with pytest.raises(ValidationError):
        AnimationFrame(timestamp_s=0.0, blendshapes=bs, emotions={}, body_pose=None)

def test_frame_clamps_out_of_range_weight():
    with pytest.raises(ValidationError):
        AnimationFrame(timestamp_s=0.0, blendshapes={"JawOpen": 2.0}, emotions={}, body_pose=None)
