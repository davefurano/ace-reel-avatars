"""Runnable demo: a 3-piece Avatar House Band performing a synthetic 120 BPM click track.

No credentials, no GPU, no ffmpeg, no Unreal needed. It generates its own audio, fakes the music
source and the Audio2Face vocal stream, runs the REAL beat detection + arranger, and renders to the
Mac-side NullBandRenderTarget — then prints what each member would perform.

    python examples/demo_band.py
"""
from __future__ import annotations
import os
import tempfile
import numpy as np
import soundfile as sf

import ace_reel.band.orchestrator as bo
from ace_reel.band.orchestrator import BandOrchestrator
from ace_reel.band.roster import load_band
from ace_reel.contracts.interfaces import MusicSource, AceClient, Track
from ace_reel.contracts.frame import AnimationFrame
from ace_reel.render.band_base import NullBandRenderTarget

_HERE = os.path.dirname(__file__)


def _make_click_wav(path: str, bpm: int = 120, sr: int = 22050, seconds: int = 8) -> None:
    """Write a short click track so librosa has real beats to detect."""
    n = sr * seconds
    audio = np.zeros(n, dtype=np.float32)
    step = int(sr * 60 / bpm)
    for i in range(0, n, step):
        audio[i:i + 200] = 0.9
    sf.write(path, audio, sr)


class ClickTrackMusic(MusicSource):
    """Stand-in MusicSource: serves the generated click track instead of the Suno catalog."""
    def __init__(self, wav_path: str):
        self._wav = wav_path

    def get_track(self, track_id: str) -> Track:
        return Track(id=track_id, title="Demo Click Track (120 BPM)",
                     duration_s=8, audio_url="file://" + self._wav)

    def read_audio(self, track: Track) -> bytes:
        with open(self._wav, "rb") as f:
            return f.read()


class HummingAce(AceClient):
    """Stand-in for Audio2Face-3D: emits jaw-open frames (no NVIDIA key required)."""
    def stream(self, pcm_16k_mono: bytes, emotions=None):
        for i in range(30):
            yield AnimationFrame(timestamp_s=i / 30,
                                 blendshapes={"JawOpen": 0.5 if i % 2 else 0.1},
                                 emotions={}, body_pose=None)


def main() -> None:
    # The fake A2F ignores the PCM, so skip the real ffmpeg transcode for a zero-dependency demo.
    bo.to_pcm_16k_mono_bytes = lambda src: src

    fd, wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        _make_click_wav(wav)
        music = ClickTrackMusic(wav)
        band = load_band(os.path.join(_HERE, "..", "bands", "demo_trio.json"))
        target = NullBandRenderTarget()
        BandOrchestrator(music, HummingAce(), target).perform("demo-001", band)

        members, _audio_len, arrangement = target.opened_with
        cues = sum(len(c) for c in arrangement.values())
        print(f"{band.name}: {len(members)} members "
              f"(vocalist {band.vocalist.avatar} + {len(arrangement)} instrumentalists)")
        print(f"  vocal frames streamed : {len(target.vocal_received)}")
        for member, member_cues in arrangement.items():
            print(f"  {member.role.value:6s} {member.avatar:14s} -> {len(member_cues):2d} cues "
                  f"(clips: {', '.join(member.clips)})")
        print(f"  total instrument cues : {cues}")
    finally:
        if os.path.exists(wav):
            os.unlink(wav)


if __name__ == "__main__":
    main()
