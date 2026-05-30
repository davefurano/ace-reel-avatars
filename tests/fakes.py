from ace_reel.contracts.interfaces import MusicSource, AceClient, Track
from ace_reel.contracts.frame import AnimationFrame
from ace_reel.render.base import NullRenderTarget

class FakeMusicSource(MusicSource):
    def get_track(self, track_id): return Track(track_id, "Fake", 10, "https://x/a.mp3")
    def read_audio(self, track): return b"SRCAUDIO"

class FakeAceClient(AceClient):
    def stream(self, pcm_16k_mono, emotions=None):
        yield AnimationFrame(timestamp_s=0.0, blendshapes={"JawOpen":0.5}, emotions={}, body_pose=None)
        yield AnimationFrame(timestamp_s=0.033, blendshapes={"JawOpen":0.1}, emotions={}, body_pose=None)
