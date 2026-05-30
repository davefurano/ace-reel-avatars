"""Stream a song through ACE into a render target."""
from __future__ import annotations
import subprocess
from ace_reel.contracts.interfaces import MusicSource, AceClient, RenderTarget

def to_pcm_16k_mono_bytes(src_audio: bytes) -> bytes:
    """ffmpeg transcode from in-memory source bytes to PCM s16le mono 16 kHz."""
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le",
         "-ac", "1", "-ar", "16000", "pipe:1"],
        input=src_audio, check=True, stdout=subprocess.PIPE,
    )
    return p.stdout

class Orchestrator:
    def __init__(self, music: MusicSource, ace: AceClient, render: RenderTarget):
        self._music, self._ace, self._render = music, ace, render

    def perform(self, track_id: str, avatar_asset: str,
                emotions: dict[str, float] | None = None) -> None:
        track = self._music.get_track(track_id)
        pcm = to_pcm_16k_mono_bytes(self._music.read_audio(track))
        frames = self._ace.stream(pcm, emotions)
        self._render.run(avatar_asset, pcm, frames)
