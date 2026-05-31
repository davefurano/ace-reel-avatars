"""Drive a full band performance from one track: music -> beats+A2F -> band render target."""
from __future__ import annotations
import os, tempfile
from ace_reel.contracts.interfaces import MusicSource, AceClient
from ace_reel.orchestrator import to_pcm_16k_mono_bytes
from ace_reel.motion.beat import detect_beats
from ace_reel.band.roster import Band
from ace_reel.band.arranger import BandArranger
from ace_reel.band.performance import BandPerformance
from ace_reel.render.band_base import BandRenderTarget


class BandOrchestrator:
    def __init__(self, music: MusicSource, ace: AceClient, render: BandRenderTarget):
        self._music, self._ace, self._render = music, ace, render

    def perform(self, track_id: str, band: Band,
                emotions: dict[str, float] | None = None) -> None:
        track = self._music.get_track(track_id)
        src = self._music.read_audio(track)
        pcm = to_pcm_16k_mono_bytes(src)
        tmp = self._source_to_tempfile(src)
        try:
            beats = detect_beats(tmp)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        arrangement = BandArranger().arrange(beats, band)
        vocal_frames = self._ace.stream(pcm, emotions)
        perf = BandPerformance(track=track, audio_pcm=pcm, vocalist=band.vocalist,
                               vocal_frames=vocal_frames, instrument_arrangement=arrangement)
        self._render.run(perf)

    @staticmethod
    def _source_to_tempfile(src: bytes) -> str:
        fd, path = tempfile.mkstemp(suffix=".audio")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(src)
        except Exception:
            os.unlink(path)
            raise
        return path
