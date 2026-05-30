import os, pytest
from ace_reel.ace.ace_client import A2FClient, A2FRawFrame, to_pcm_16k_mono
from ace_reel.contracts.frame import AnimationFrame


class FakeTransport:
    def process(self, pcm, emotions):
        yield A2FRawFrame(names=["JawOpen"], weights=[0.6], timecode_s=0.0,
                          emotions={"joy": 0.4})
        yield A2FRawFrame(names=["JawOpen"], weights=[0.1], timecode_s=0.033,
                          emotions={"joy": 0.4})


def test_client_wraps_raw_frames_into_animation_frames():
    client = A2FClient(transport=FakeTransport())
    frames = list(client.stream(b"\x00\x00" * 16000))
    assert all(isinstance(f, AnimationFrame) for f in frames)
    assert frames[0].blendshapes["JawOpen"] == pytest.approx(0.6)
    assert frames[0].emotions["joy"] == pytest.approx(0.4)
    assert frames[1].timestamp_s == pytest.approx(0.033)


@pytest.mark.live
def test_live_hosted_a2f_returns_frames():
    if not os.getenv("NVIDIA_API_KEY"):
        pytest.skip("no NVIDIA_API_KEY")
    from ace_reel.ace.ace_client import NvcfA2FTransport
    pcm = to_pcm_16k_mono("tests/data/sample_vocal.wav")
    client = A2FClient(transport=NvcfA2FTransport())
    frames = list(client.stream(pcm))
    assert len(frames) > 10
    assert "JawOpen" in frames[0].blendshapes
