import pytest
from ace_reel.render.unreal_livelink import UnrealRenderTarget
from ace_reel.contracts.interfaces import RenderTarget


def test_is_a_render_target():
    assert issubclass(UnrealRenderTarget, RenderTarget)


def test_open_raises_clear_unsupported_error():
    t = UnrealRenderTarget()
    with pytest.raises(NotImplementedError) as e:
        t.open("Avatar_Claire", b"\x00\x00")
    assert "Windows" in str(e.value) and "setup-reel-engine" in str(e.value)
