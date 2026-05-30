from ace_reel.render.base import NullRenderTarget
from ace_reel.contracts.frame import AnimationFrame


def _frame(ts):
    return AnimationFrame(timestamp_s=ts, blendshapes={"JawOpen": 0.3}, emotions={}, body_pose=None)


def test_null_target_records_open_frames_close_in_order():
    t = NullRenderTarget()
    t.run("Avatar_Claire", b"\x00\x00", [_frame(0.0), _frame(0.033)])
    assert t.opened_with == ("Avatar_Claire", 2)        # asset, audio byte-count
    assert [f.timestamp_s for f in t.received] == [0.0, 0.033]
    assert t.closed is True
